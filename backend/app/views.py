import hashlib
import json
import os
import re
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET

TRANSFERMARKT_SITE_BASE = os.environ.get(
    "TRANSFERMARKT_SITE_BASE", "https://www.transfermarkt.com"
).rstrip("/")

TRANSFERMARKT_UK_BASE = os.environ.get(
    "TRANSFERMARKT_UK_BASE", "https://www.transfermarkt.co.uk"
).rstrip("/")

MARKET_VALUE_CEAPI = f"{TRANSFERMARKT_SITE_BASE}/ceapi/marketValueDevelopment/graph"
TRANSFER_HISTORY_CEAPI = f"{TRANSFERMARKT_UK_BASE}/ceapi/transferHistory/list"

REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "25"))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", str(60 * 60 * 6)))

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
)


class TransfermarktProxyError(Exception):
    pass


def error_response(message: str, status: int = 502) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


def build_cache_key(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"footyfinder:{prefix}:{digest}"


def normalize_query(value: str) -> str:
    return " ".join((value or "").replace("%20", " ").split())


def format_date(value) -> str:
    if not value:
        return ""

    value = str(value).strip()

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.strptime(value, fmt).strftime("%b %d, %Y")
        except ValueError:
            pass

    return value


def format_height(value) -> str:
    if not value:
        return ""

    value = str(value).strip().replace(",", ".")
    if value.endswith(" m"):
        return value

    try:
        centimeters = int(float(value))
        return f"{centimeters / 100:.2f} m"
    except (TypeError, ValueError):
        return str(value)


def format_days(value) -> str:
    if value in (None, ""):
        return ""

    value = str(value).strip()
    if "day" in value.lower():
        return value

    try:
        days = int(float(value))
        return f"{days} day" if days == 1 else f"{days} days"
    except (TypeError, ValueError):
        return value


def format_money(value) -> str:
    if value in (None, "", "-", "nan"):
        return "-"

    if isinstance(value, str) and "€" in value:
        return value.strip()

    try:
        amount = int(float(value))
    except (TypeError, ValueError):
        return str(value).strip()

    absolute_amount = abs(amount)
    if absolute_amount >= 1_000_000:
        formatted = f"€{amount / 1_000_000:.1f}m"
    elif absolute_amount >= 1_000:
        formatted = f"€{amount / 1_000:.0f}k"
    else:
        formatted = f"€{amount}"

    return formatted.replace(".0m", "m")


def join_parts(parts, separator=", ") -> str:
    filtered = [str(part).strip() for part in parts if part not in (None, "", [], {})]
    return separator.join(filtered)


def clean_html_text(value) -> str:
    if value in (None, ""):
        return ""

    if not isinstance(value, str):
        return str(value)

    if "<" in value and ">" in value:
        value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)

    value = value.replace("\xa0", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def decode_transfermarkt_text(value) -> str:
    value = clean_html_text(value)
    if not value:
        return ""

    try:
        value = bytes(value, "utf-8").decode("unicode_escape")
    except Exception:
        pass

    value = value.replace("\\x20", " ").replace("\\/", "/")
    value = re.sub(r"\s+", " ", value).strip()
    return value

def extract_club_name(value) -> str:
    if isinstance(value, dict):
        return decode_transfermarkt_text(
            value.get("clubName")
            or value.get("name")
            or value.get("title")
            or ""
        )

    return decode_transfermarkt_text(value)


def parse_card_triplet(value: str):
    value = clean_html_text(value)
    parts = [part.strip() for part in value.split("/")]

    while len(parts) < 3:
        parts.append("-")

    yellow = parts[0] if parts[0] != "-" else "0"
    red = parts[2] if parts[2] != "-" else "0"

    return yellow, red


def request_html(url: str, params=None) -> str:
    cache_key = build_cache_key("html", f"{url}|{params or {}}")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = SESSION.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TransfermarktProxyError("Could not fetch player data right now.") from exc

    cache.set(cache_key, response.text, CACHE_TTL_SECONDS)
    return response.text


def request_json(url: str, params=None):
    cache_key = build_cache_key("json", f"{url}|{params or {}}")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = SESSION.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TransfermarktProxyError("Could not fetch player data right now.") from exc

    try:
        payload = response.json()
    except ValueError:
        try:
            payload = json.loads(response.text)
        except Exception as exc:
            raise TransfermarktProxyError("Could not parse player data right now.") from exc

    cache.set(cache_key, payload, CACHE_TTL_SECONDS)
    return payload


def cache_player_meta(player: dict):
    player_id = str(player.get("id") or "").strip()
    if player_id:
        cache.set(f"footyfinder:player-meta:{player_id}", player, CACHE_TTL_SECONDS)


def get_player_meta(player_id: str) -> dict:
    return cache.get(f"footyfinder:player-meta:{player_id}") or {"id": str(player_id), "slug": "-"}


def build_player_page_url(player_meta: dict, section: str, suffix: str = "") -> str:
    slug = player_meta.get("slug") or "-"
    player_id = player_meta.get("id") or ""
    return f"{TRANSFERMARKT_SITE_BASE}/{slug}/{section}/{player_id}{suffix}"


def search_transfermarkt_site(query: str) -> list[dict]:
    cache_key = build_cache_key("site-search", query)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{TRANSFERMARKT_SITE_BASE}/schnellsuche/ergebnis/schnellsuche"
    html = request_html(url, params={"query": query})
    soup = BeautifulSoup(html, "html.parser")

    results = []
    seen = set()

    for row in soup.select("table.items tbody tr"):
        link = row.select_one('a[href*="/profil/spieler/"]')
        if not link:
            continue

        href = (link.get("href") or "").strip()
        match = re.search(r"/spieler/(\d+)", href)
        if not match:
            continue

        player_id = match.group(1)
        if player_id in seen:
            continue
        seen.add(player_id)

        parts = href.strip("/").split("/")
        slug = parts[0] if len(parts) >= 4 else "-"
        full_href = href if href.startswith("http") else f"{TRANSFERMARKT_SITE_BASE}{href}"

        img = row.select_one("img")
        picture = ""
        if img:
            picture = img.get("data-src") or img.get("src") or ""

        name = (link.get("title") or link.get_text(" ", strip=True) or "").strip()

        first_hauptlink = row.select_one("td.hauptlink")
        position = ""
        if first_hauptlink:
            parts_text = [
                part.strip()
                for part in first_hauptlink.get_text("\n", strip=True).split("\n")
                if part.strip()
            ]
            filtered = [part for part in parts_text if part != name]
            if filtered:
                position = filtered[0]

        club = ""
        for anchor in row.select("a[href]"):
            href_value = anchor.get("href") or ""
            text = anchor.get_text(" ", strip=True)
            if text and "/verein/" in href_value:
                club = text

        age = ""
        for td in row.select("td"):
            raw = td.get_text(" ", strip=True).strip()
            if raw.isdigit():
                number = int(raw)
                if 15 <= number <= 45:
                    age = str(number)
                    break

        market_value = "-"
        for td in reversed(row.select("td")):
            raw = td.get_text(" ", strip=True)
            if "€" in raw:
                market_value = raw.strip()
                break

        item = {
            "id": player_id,
            "slug": slug,
            "href": full_href,
            "name": name,
            "position": position,
            "club": club,
            "age": age,
            "marketValue": market_value,
            "picture": picture,
        }

        cache_player_meta(item)
        results.append(item)

    cache.set(cache_key, results, CACHE_TTL_SECONDS)
    return results


def resolve_player_from_name(query: str) -> dict:
    results = search_transfermarkt_site(query)
    if not results:
        raise TransfermarktProxyError("Player not found.")

    query_cf = query.casefold()
    for item in results:
        if (item.get("name") or "").casefold() == query_cf:
            return item

    return results[0]


def scrape_profile_from_meta(player_meta: dict) -> dict:
    url = build_player_page_url(player_meta, "profil/spieler")
    html = request_html(url)
    soup = BeautifulSoup(html, "html.parser")

    image = ""
    image_tag = soup.select_one(
        ".data-header__profile-image img, div.modal-trigger img, img.bilderrahmen-fixed"
    )
    if image_tag:
        image = image_tag.get("src") or image_tag.get("data-src") or ""

    info = {
        "picture": image or player_meta.get("picture") or "",
        "Name": player_meta.get("name") or "",
        "id": player_meta.get("id") or "",
    }

    table = soup.find(
        "div",
        {"class": "info-table info-table--right-space min-height-audio"},
    )
    if table is None:
        table = soup.find("div", {"class": "info-table info-table--right-space"})

    if table is not None:
        prev = ""
        index = 0
        for line in table.get_text("\n", strip=True).split("\n"):
            value = line.strip().replace(":", "")
            if not value:
                continue

            if index % 2 == 0:
                info[value] = ""
                prev = value
            else:
                info[prev] = value
            index += 1

    cleaned = {
        key: value
        for key, value in info.items()
        if key in {"picture", "id"} or value not in (None, "", [], {})
    }

    return cleaned


def pick_stats_table(tables):
    for table in tables:
        if len(table.columns) >= 9 and len(table) > 0:
            return table
    return None


def pick_injuries_table(tables):
    for table in tables:
        if len(table.columns) >= 6 and len(table) > 0:
            return table
    return None


@require_GET
def index(request):
    return JsonResponse({"service": "FootyFinder API", "status": "ok"})


@require_GET
def search(request, query: str) -> JsonResponse:
    try:
        query = normalize_query(query)
        if not query:
            return JsonResponse({"results": []})
        return JsonResponse({"results": search_transfermarkt_site(query)[:8]})
    except TransfermarktProxyError as exc:
        return error_response(str(exc))


@require_GET
def profile(request, name: str) -> JsonResponse:
    try:
        query = normalize_query(name)
        if not query:
            return error_response("Please enter a player name.", 400)

        player_meta = resolve_player_from_name(query)
        return JsonResponse(scrape_profile_from_meta(player_meta))
    except TransfermarktProxyError as exc:
        return error_response(str(exc))


@require_GET
def profile_by_id(request, player_id: str) -> JsonResponse:
    try:
        if not player_id:
            return error_response("Missing player id.", 400)

        player_meta = get_player_meta(player_id)
        player_meta["id"] = str(player_id)
        return JsonResponse(scrape_profile_from_meta(player_meta))
    except TransfermarktProxyError as exc:
        return error_response(str(exc))


@require_GET
def stats(request, player_id: str) -> JsonResponse:
    try:
        player_meta = get_player_meta(player_id)
        url = build_player_page_url(
            player_meta,
            "leistungsdatendetails/spieler",
            "/saison//verein/0/liga/0/wettbewerb//pos/0/trainer_id/0",
        )
        html = request_html(url)
        tables = pd.read_html(StringIO(html), flavor="lxml")
        table = pick_stats_table(tables)

        if table is None:
            return JsonResponse(
                {
                    "header": [
                        "Season",
                        "Competition",
                        "Appearances",
                        "Goals",
                        "Assists",
                        "Yellow Cards",
                        "Red Cards",
                        "Minutes",
                    ],
                    "body": [],
                }
            )

        body = []
        for _, row in table.iterrows():
            values = [clean_html_text(value) for value in row.tolist()]
            if len(values) < 9:
                continue

            if str(values[0]).strip().lower().startswith("total"):
                continue

            yellow, red = parse_card_triplet(values[7])

            body.append(
                [
                    values[0],
                    values[2],
                    values[4],
                    values[5],
                    values[6],
                    yellow,
                    red,
                    values[8],
                ]
            )

        return JsonResponse(
            {
                "header": [
                    "Season",
                    "Competition",
                    "Appearances",
                    "Goals",
                    "Assists",
                    "Yellow Cards",
                    "Red Cards",
                    "Minutes",
                ],
                "body": body,
            }
        )
    except TransfermarktProxyError as exc:
        return error_response(str(exc))
    except Exception:
        return error_response("Could not parse stats right now.")


@require_GET
def injuries(request, player_id: str) -> JsonResponse:
    try:
        player_meta = get_player_meta(player_id)
        url = build_player_page_url(player_meta, "verletzungen/spieler", "/plus/1")
        html = request_html(url)
        tables = pd.read_html(StringIO(html), flavor="lxml")
        table = pick_injuries_table(tables)

        if table is None:
            return JsonResponse(
                {
                    "header": ["Season", "Injury", "From", "Until", "Days", "Games Missed"],
                    "body": [],
                }
            )

        body = []
        for _, row in table.iterrows():
            values = [clean_html_text(value) for value in row.tolist()]
            if len(values) < 6:
                continue

            if str(values[0]).strip().lower().startswith("total"):
                continue

            body.append(
                [
                    values[0],
                    values[1],
                    values[2],
                    values[3],
                    values[4],
                    values[5],
                ]
            )

        return JsonResponse(
            {
                "header": ["Season", "Injury", "From", "Until", "Days", "Games Missed"],
                "body": body,
            }
        )
    except TransfermarktProxyError as exc:
        return error_response(str(exc))
    except Exception:
        return error_response("Could not parse injury history right now.")


@require_GET
def value(request, player_id: str) -> JsonResponse:
    try:
        payload = request_json(f"{MARKET_VALUE_CEAPI}/{player_id}")
        rows = payload if isinstance(payload, list) else payload.get("data") or payload.get("list") or []

        result = []
        for item in rows:
            if not isinstance(item, dict):
                continue

            club_name = decode_transfermarkt_text(
                item.get("verein")
                or item.get("clubName")
                or item.get("club_name")
                or item.get("club")
                or ""
            )

            result.append(
                {
                    "age": "",
                    "date": format_date(item.get("datum_mw") or item.get("date") or item.get("datum")),
                    "clubName": club_name,
                    "value": format_money(item.get("y") or item.get("value") or item.get("market_value")),
                }
            )

        return JsonResponse({"result": result})
    except TransfermarktProxyError as exc:
        return error_response(str(exc))
    except Exception:
        return error_response("Could not parse market value history right now.")


@require_GET
def transfers(request, player_id: str) -> JsonResponse:
    try:
        payload = request_json(f"{TRANSFER_HISTORY_CEAPI}/{player_id}")
        rows = payload if isinstance(payload, list) else payload.get("data") or payload.get("transfers") or []

        body = []
        for item in rows:
            if not isinstance(item, dict):
                continue

            season = clean_html_text(item.get("saison") or item.get("season") or "")
            date = format_date(item.get("datum") or item.get("date") or "")
            from_club = extract_club_name(
                item.get("abgebender_verein")
                or item.get("from")
                or item.get("from_club")
                or item.get("club_from")
                or item.get("clubFrom")
                or ""
            )

            to_club = extract_club_name(
                item.get("aufnehmender_verein")
                or item.get("to")
                or item.get("to_club")
                or item.get("club_to")
                or item.get("clubTo")
                or ""
            )
            market_value = format_money(item.get("marktwert") or item.get("market_value") or item.get("marketValue"))
            fee = clean_html_text(item.get("abloese") or item.get("fee") or item.get("transfer_fee") or item.get("transferFee") or "-")

            if fee != "-" and "€" not in fee:
                fee = format_money(fee)

            body.append([season, date, from_club or "-", to_club or "-", market_value, fee or "-"])

        return JsonResponse(
            {
                "header": ["Season", "Date", "From", "To", "Market Value", "Fee"],
                "body": body,
            }
        )
    except TransfermarktProxyError as exc:
        return error_response(str(exc))
    except Exception:
        return error_response("Could not parse transfer history right now.")