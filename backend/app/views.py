import hashlib
import os
import re
import time
from datetime import datetime
from io import StringIO
import logging

import pandas as pd
import requests
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

TRANSFERMARKT_SITE_BASE = os.environ.get(
    "TRANSFERMARKT_SITE_BASE", "https://www.transfermarkt.com"
).rstrip("/")

TRANSFERMARKT_US_BASE = os.environ.get(
    "TRANSFERMARKT_US_BASE", "https://www.transfermarkt.us"
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

logger = logging.getLogger(__name__)

STATS_HEADER = [
    "Season",
    "Competition",
    "Appearances",
    "Goals",
    "Assists",
    "Yellow Cards",
    "Red Cards",
    "Minutes",
]


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


def zero_if_empty(value) -> str:
    value = clean_html_text(value)
    return "0" if value in ("", "-", "–", "nan", "NaN", "None") else value


def request_html(url: str, params=None) -> str:
    cache_key = build_cache_key("html", f"{url}|{params or {}}")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = SESSION.get(url, params=params, timeout=REQUEST_TIMEOUT)

        if not response.ok:
            logger.error(
                "Transfermarkt HTML request failed | status=%s | url=%s | final_url=%s | body=%s",
                response.status_code,
                url,
                getattr(response, "url", url),
                response.text[:500],
            )
            raise TransfermarktProxyError("Could not fetch player data right now.")

    except requests.RequestException:
        logger.exception(
            "Transfermarkt HTML request exception | url=%s | params=%s",
            url,
            params,
        )
        raise TransfermarktProxyError("Could not fetch player data right now.")

    cache.set(cache_key, response.text, CACHE_TTL_SECONDS)
    return response.text


def request_rendered_html(url: str) -> str:
    """
    Transfermarkt's detailed stats page is now rendered by JavaScript.
    requests/pandas can fetch the shell page, but not the rows.
    For the local demo, use Selenium only for the Stats tab.
    """
    cache_key = build_cache_key("rendered-html", url)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1400,1200")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    driver = None

    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)

        WebDriverWait(driver, REQUEST_TIMEOUT).until(
            lambda browser: (
                len(browser.find_elements(By.CSS_SELECTOR, 'div[role="row"].grid-row .tm-grid__cell')) > 0
                or "Access denied" in browser.page_source
                or "Attention Required" in browser.page_source
            )
        )

        html = driver.page_source

        if "Access denied" in html or "Attention Required" in html:
            raise TransfermarktProxyError("Transfermarkt blocked the rendered stats request right now.")

        cache.set(cache_key, html, CACHE_TTL_SECONDS)
        return html

    except TransfermarktProxyError:
        raise
    except Exception:
        logger.exception("Selenium rendered request failed | url=%s", url)
        raise TransfermarktProxyError("Could not fetch rendered stats right now.")
    finally:
        if driver is not None:
            driver.quit()


def request_json(url: str, params=None):
    cache_key = build_cache_key("json", f"{url}|{params or {}}")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        response = SESSION.get(url, params=params, timeout=REQUEST_TIMEOUT)

        if not response.ok:
            logger.error(
                "Transfermarkt JSON request failed | status=%s | url=%s | final_url=%s | body=%s",
                response.status_code,
                url,
                getattr(response, "url", url),
                response.text[:500],
            )
            raise TransfermarktProxyError("Could not fetch player data right now.")

    except requests.RequestException:
        logger.exception(
            "Transfermarkt JSON request exception | url=%s | params=%s",
            url,
            params,
        )
        raise TransfermarktProxyError("Could not fetch player data right now.")

    try:
        payload = response.json()
    except ValueError:
        logger.error(
            "Transfermarkt JSON parse failed | url=%s | body=%s",
            getattr(response, "url", url),
            response.text[:500],
        )
        raise TransfermarktProxyError("Could not parse player data right now.")

    cache.set(cache_key, payload, CACHE_TTL_SECONDS)
    return payload


def cache_player_meta(player: dict):
    player_id = str(player.get("id") or "").strip()
    if player_id:
        cache.set(f"footyfinder:player-meta:{player_id}", player, CACHE_TTL_SECONDS)


def get_player_meta(player_id: str) -> dict:
    return cache.get(f"footyfinder:player-meta:{player_id}") or {
        "id": str(player_id),
        "slug": "-",
    }


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


def pick_injuries_table(tables):
    for table in tables:
        if len(table.columns) >= 6 and len(table) > 0:
            return table
    return None


def current_season_start_year() -> int:
    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1


def current_season_label() -> str:
    start_year = current_season_start_year()
    return f"{str(start_year)[-2:]}/{str(start_year + 1)[-2:]}"


def get_season_from_row(row) -> str:
    link = row.select_one('a[href*="/saison/"]')
    if not link:
        return current_season_label()

    href = link.get("href") or ""
    match = re.search(r"/saison/(\d{4})", href)
    if not match:
        return current_season_label()

    start_year = int(match.group(1))
    return f"{str(start_year)[-2:]}/{str(start_year + 1)[-2:]}"


def parse_stats_with_soup(html: str) -> list[list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    parsed_rows = []

    # Transfermarkt detailed stats are rendered as a custom div grid, not a normal table.
    for row in soup.select('div[role="row"].grid-row'):
        cells = row.select(".tm-grid__cell")

        if len(cells) < 15:
            continue

        competition_cell = cells[0]
        competition_link = competition_cell.select_one("a")

        if competition_link:
            competition = clean_html_text(
                competition_link.get("title")
                or competition_link.get_text(" ", strip=True)
            )
        else:
            competition = clean_html_text(
                competition_cell.get("title")
                or competition_cell.get_text(" ", strip=True)
            )

        if not competition:
            continue

        values = [clean_html_text(cell.get_text(" ", strip=True)) for cell in cells]

        parsed_rows.append(
            [
                get_season_from_row(row),
                competition,
                zero_if_empty(values[2] if len(values) > 2 else "0"),
                zero_if_empty(values[4] if len(values) > 4 else "0"),
                zero_if_empty(values[5] if len(values) > 5 else "0"),
                zero_if_empty(values[7] if len(values) > 7 else "0"),
                zero_if_empty(values[9] if len(values) > 9 else "0"),
                clean_html_text(values[14] if len(values) > 14 else "-") or "-",
            ]
        )

    return parsed_rows


def get_stats_candidate_urls(player_meta: dict, player_id: str) -> list[str]:
    slug = player_meta.get("slug") or "-"

    if slug == "-":
        urls = [
            f"{TRANSFERMARKT_US_BASE}/-/leistungsdatendetails/spieler/{player_id}/plus/1",
            f"{TRANSFERMARKT_SITE_BASE}/-/leistungsdatendetails/spieler/{player_id}/plus/1",
        ]
    else:
        urls = [
            f"{TRANSFERMARKT_US_BASE}/{slug}/leistungsdatendetails/spieler/{player_id}/plus/1",
            f"{TRANSFERMARKT_SITE_BASE}/{slug}/leistungsdatendetails/spieler/{player_id}/plus/1",
        ]

    seen = set()
    unique_urls = []

    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


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



INJURIES_HEADER = ["Season", "Injury", "From", "Until", "Days", "Games Missed"]
TRANSFERS_HEADER = ["Season", "Date", "From", "To", "Market Value", "Fee"]


def number_from_text(value) -> int:
    value = clean_html_text(value)
    if value in ("", "-", "–", "nan", "NaN", "None"):
        return 0

    digits = re.sub(r"[^0-9-]", "", value)
    if digits in ("", "-"):
        return 0

    try:
        return int(digits)
    except ValueError:
        return 0


def parse_money_to_number(value):
    value = clean_html_text(value)
    if not value or value in ("-", "–", "nan", "NaN", "None", "free transfer", "End of loan"):
        return None

    lowered = value.lower().replace(",", ".")
    match = re.search(r"€\s*([0-9]+(?:\.[0-9]+)?)\s*([kmb])?", lowered)
    if not match:
        return None

    amount = float(match.group(1))
    suffix = match.group(2)

    if suffix == "b":
        amount *= 1_000_000_000
    elif suffix == "m":
        amount *= 1_000_000
    elif suffix == "k":
        amount *= 1_000

    return int(amount)


def display_number(value) -> str:
    return f"{int(value):,}" if value not in (None, "") else "0"


def display_decimal(value, digits=2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "0.00"


def aggregate_stats_rows(body: list[list[str]]) -> dict:
    totals = {
        "appearances": 0,
        "goals": 0,
        "assists": 0,
        "yellowCards": 0,
        "redCards": 0,
        "minutes": 0,
        "goalContributions": 0,
    }
    seasons = {}
    competitions = {}

    for row in body:
        if len(row) < 8:
            continue

        season = row[0] or "Unknown"
        competition = row[1] or "Unknown"
        appearances = number_from_text(row[2])
        goals = number_from_text(row[3])
        assists = number_from_text(row[4])
        yellow_cards = number_from_text(row[5])
        red_cards = number_from_text(row[6])
        minutes = number_from_text(row[7])

        totals["appearances"] += appearances
        totals["goals"] += goals
        totals["assists"] += assists
        totals["yellowCards"] += yellow_cards
        totals["redCards"] += red_cards
        totals["minutes"] += minutes
        totals["goalContributions"] += goals + assists

        for bucket, key in ((seasons, season), (competitions, competition)):
            item = bucket.setdefault(
                key,
                {
                    "name": key,
                    "appearances": 0,
                    "goals": 0,
                    "assists": 0,
                    "minutes": 0,
                    "goalContributions": 0,
                },
            )
            item["appearances"] += appearances
            item["goals"] += goals
            item["assists"] += assists
            item["minutes"] += minutes
            item["goalContributions"] += goals + assists

    minutes = totals["minutes"]
    totals["goalsPer90"] = round((totals["goals"] * 90 / minutes), 2) if minutes else 0
    totals["assistsPer90"] = round((totals["assists"] * 90 / minutes), 2) if minutes else 0
    totals["contributionsPer90"] = round((totals["goalContributions"] * 90 / minutes), 2) if minutes else 0
    totals["minutesDisplay"] = display_number(minutes)

    season_breakdown = list(seasons.values())
    competition_breakdown = sorted(
        competitions.values(),
        key=lambda item: (item["goalContributions"], item["appearances"]),
        reverse=True,
    )

    best_season = max(
        season_breakdown,
        key=lambda item: (item["goalContributions"], item["goals"], item["appearances"]),
        default=None,
    )
    top_competition = competition_breakdown[0] if competition_breakdown else None

    return {
        "totals": totals,
        "seasonBreakdown": season_breakdown,
        "competitionBreakdown": competition_breakdown,
        "bestSeason": best_season,
        "topCompetition": top_competition,
        "seasonCount": len(season_breakdown),
        "competitionCount": len(competition_breakdown),
    }


def build_stats_payload(player_meta: dict, player_id: str) -> dict:
    body = []

    for url in get_stats_candidate_urls(player_meta, str(player_id)):
        try:
            html = request_html(url)
            body = parse_stats_with_soup(html)
        except TransfermarktProxyError:
            body = []

        if not body:
            html = request_rendered_html(url)
            body = parse_stats_with_soup(html)

        if body:
            break

    summary = aggregate_stats_rows(body)
    return {
        "header": STATS_HEADER,
        "body": body,
        "summary": summary["totals"],
        "seasonBreakdown": summary["seasonBreakdown"],
        "competitionBreakdown": summary["competitionBreakdown"],
        "bestSeason": summary["bestSeason"],
        "topCompetition": summary["topCompetition"],
        "seasonCount": summary["seasonCount"],
        "competitionCount": summary["competitionCount"],
    }


def build_injuries_payload(player_meta: dict) -> dict:
    url = build_player_page_url(player_meta, "verletzungen/spieler", "/plus/1")
    html = request_html(url)
    tables = pd.read_html(StringIO(html), flavor="lxml")
    table = pick_injuries_table(tables)

    body = []
    if table is not None:
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

    total_days = sum(number_from_text(row[4]) for row in body)
    total_games_missed = sum(number_from_text(row[5]) for row in body)
    longest = max(body, key=lambda row: number_from_text(row[4]), default=None)
    seasons_impacted = len({row[0] for row in body if row and row[0]})

    return {
        "header": INJURIES_HEADER,
        "body": body,
        "summary": {
            "totalInjuries": len(body),
            "totalDaysOut": total_days,
            "totalGamesMissed": total_games_missed,
            "averageDaysOut": round(total_days / len(body), 1) if body else 0,
            "longestInjury": {
                "injury": longest[1],
                "season": longest[0],
                "days": number_from_text(longest[4]),
                "from": longest[2],
                "until": longest[3],
            }
            if longest
            else None,
            "seasonsImpacted": seasons_impacted,
        },
    }


def build_value_payload(player_id: str) -> dict:
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
        formatted_value = format_money(item.get("y") or item.get("value") or item.get("market_value"))

        result.append(
            {
                "age": "",
                "date": format_date(item.get("datum_mw") or item.get("date") or item.get("datum")),
                "clubName": club_name,
                "value": formatted_value,
                "valueNumber": parse_money_to_number(formatted_value),
            }
        )

    numeric_values = [item for item in result if item.get("valueNumber") is not None]
    first = numeric_values[0] if numeric_values else None
    current = numeric_values[-1] if numeric_values else None
    peak = max(numeric_values, key=lambda item: item["valueNumber"], default=None)
    low = min(numeric_values, key=lambda item: item["valueNumber"], default=None)

    growth_value = None
    growth_percent = None
    if first and current and first["valueNumber"]:
        growth_value = current["valueNumber"] - first["valueNumber"]
        growth_percent = round((growth_value / first["valueNumber"]) * 100, 1)

    return {
        "result": result,
        "summary": {
            "currentValue": current["value"] if current else "-",
            "currentValueNumber": current["valueNumber"] if current else None,
            "peakValue": peak["value"] if peak else "-",
            "peakValueNumber": peak["valueNumber"] if peak else None,
            "peakDate": peak["date"] if peak else "",
            "lowestValue": low["value"] if low else "-",
            "firstValue": first["value"] if first else "-",
            "valueChange": format_money(growth_value) if growth_value is not None else "-",
            "valueChangeNumber": growth_value,
            "valueChangePercent": growth_percent,
            "dataPoints": len(result),
        },
    }


def build_transfers_payload(player_id: str) -> dict:
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

        market_value = format_money(
            item.get("marktwert")
            or item.get("market_value")
            or item.get("marketValue")
        )

        fee = clean_html_text(
            item.get("abloese")
            or item.get("fee")
            or item.get("transfer_fee")
            or item.get("transferFee")
            or "-"
        )

        if fee != "-" and "€" not in fee:
            fee = format_money(fee)

        body.append(
            [
                season,
                date,
                from_club or "-",
                to_club or "-",
                market_value,
                fee or "-",
            ]
        )

    fee_rows = [(row, parse_money_to_number(row[5])) for row in body]
    fee_rows = [(row, fee) for row, fee in fee_rows if fee is not None]
    known_fees = [fee for _, fee in fee_rows]
    biggest_row = max(fee_rows, key=lambda item: item[1], default=(None, None))[0]
    clubs = []
    for row in body:
        for club in (row[2], row[3]):
            if club and club != "-" and club not in clubs:
                clubs.append(club)

    return {
        "header": TRANSFERS_HEADER,
        "body": body,
        "summary": {
            "totalTransfers": len(body),
            "knownFeeTransfers": len(known_fees),
            "totalKnownFees": format_money(sum(known_fees)) if known_fees else "-",
            "totalKnownFeesNumber": sum(known_fees) if known_fees else 0,
            "biggestFee": biggest_row[5] if biggest_row else "-",
            "biggestMove": {
                "season": biggest_row[0],
                "from": biggest_row[2],
                "to": biggest_row[3],
                "fee": biggest_row[5],
            }
            if biggest_row
            else None,
            "latestMove": {
                "season": body[0][0],
                "date": body[0][1],
                "from": body[0][2],
                "to": body[0][3],
                "fee": body[0][5],
            }
            if body
            else None,
            "clubsRepresented": len(clubs),
            "clubs": clubs[:10],
        },
    }


def extract_player_age(profile_data: dict) -> str:
    value = profile_data.get("Date of birth/Age") or profile_data.get("Age") or ""
    match = re.search(r"\((\d+)\)", str(value))
    if match:
        return match.group(1)
    return clean_html_text(value)


def clamp_score(value, minimum=0, maximum=100):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0
    return max(minimum, min(maximum, round(numeric, 1)))


def score_label(value) -> str:
    value = clamp_score(value)
    if value >= 82:
        return "Excellent"
    if value >= 68:
        return "Strong"
    if value >= 50:
        return "Solid"
    if value >= 35:
        return "Watchlist"
    return "Low signal"


def build_player_story(profile_data: dict, stats_payload: dict, injuries_payload: dict, value_payload: dict, transfers_payload: dict) -> dict:
    stats_summary = stats_payload.get("summary") or {}
    injury_summary = injuries_payload.get("summary") or {}
    value_summary = value_payload.get("summary") or {}
    transfer_summary = transfers_payload.get("summary") or {}

    contributions_per_90 = float(stats_summary.get("contributionsPer90") or 0)
    goals_per_90 = float(stats_summary.get("goalsPer90") or 0)
    assists_per_90 = float(stats_summary.get("assistsPer90") or 0)
    total_days_out = int(injury_summary.get("totalDaysOut") or 0)
    value_change_percent = value_summary.get("valueChangePercent")
    transfer_count = int(transfer_summary.get("totalTransfers") or 0)
    age = extract_player_age(profile_data)

    badges = []
    if contributions_per_90 >= 0.7:
        badges.append("Elite output")
    elif contributions_per_90 >= 0.4:
        badges.append("Strong final-third production")

    if total_days_out == 0:
        badges.append("No listed injury absences")
    elif total_days_out <= 45:
        badges.append("Low injury downtime")
    elif total_days_out >= 150:
        badges.append("High injury history")

    if isinstance(value_change_percent, (int, float)):
        if value_change_percent >= 100:
            badges.append("Major market-value growth")
        elif value_change_percent <= -40:
            badges.append("Market value decline")

    if transfer_summary.get("clubsRepresented", 0) >= 5:
        badges.append("Multi-club career path")

    if not badges:
        badges.append("Balanced profile")

    productivity_score = clamp_score(contributions_per_90 * 100)
    availability_score = clamp_score(100 - (total_days_out / 6))
    market_score = 50
    if isinstance(value_change_percent, (int, float)):
        market_score = clamp_score(50 + value_change_percent / 4)

    movement_score = clamp_score(100 - min(transfer_count, 8) * 8)
    discipline_score = clamp_score(100 - (int(stats_summary.get("yellowCards") or 0) * 0.8) - (int(stats_summary.get("redCards") or 0) * 7))
    overall_score = clamp_score(
        productivity_score * 0.32
        + availability_score * 0.22
        + market_score * 0.2
        + movement_score * 0.14
        + discipline_score * 0.12
    )

    return {
        "name": profile_data.get("Name") or "Selected player",
        "position": profile_data.get("Position") or "-",
        "club": profile_data.get("Current club") or "-",
        "age": age,
        "badges": badges,
        "scores": {
            "overall": overall_score,
            "productivity": productivity_score,
            "availability": availability_score,
            "marketMomentum": market_score,
            "careerStability": movement_score,
            "discipline": discipline_score,
            "goalsPer90": goals_per_90,
            "assistsPer90": assists_per_90,
        },
        "scoreLabels": {
            "overall": score_label(overall_score),
            "productivity": score_label(productivity_score),
            "availability": score_label(availability_score),
            "marketMomentum": score_label(market_score),
            "careerStability": score_label(movement_score),
            "discipline": score_label(discipline_score),
        },
        "headlineMetrics": [
            {"label": "Overall score", "value": display_decimal(overall_score, 1)},
            {"label": "Career apps", "value": display_number(stats_summary.get("appearances") or 0)},
            {"label": "Goals + assists", "value": display_number(stats_summary.get("goalContributions") or 0)},
            {"label": "G+A per 90", "value": display_decimal(stats_summary.get("contributionsPer90") or 0)},
            {"label": "Peak value", "value": value_summary.get("peakValue") or "-"},
            {"label": "Days out", "value": display_number(injury_summary.get("totalDaysOut") or 0)},
        ],
    }


def build_value_analysis(value_payload: dict) -> dict:
    rows = [row for row in value_payload.get("result", []) if row.get("valueNumber") is not None]
    summary = value_payload.get("summary") or {}

    if not rows:
        return {
            "trendLabel": "No market data",
            "volatilityLabel": "Unknown",
            "latestMove": "-",
            "range": [],
            "scenarioCards": [],
        }

    current = rows[-1]
    previous = rows[-2] if len(rows) >= 2 else None
    peak_value = summary.get("peakValueNumber") or current.get("valueNumber") or 0
    low_value = min(row["valueNumber"] for row in rows)
    current_value = current.get("valueNumber") or 0

    latest_change = None
    latest_change_percent = None
    if previous and previous.get("valueNumber"):
        latest_change = current_value - previous["valueNumber"]
        latest_change_percent = round((latest_change / previous["valueNumber"]) * 100, 1)

    range_spread = peak_value - low_value if peak_value else 0
    volatility = round((range_spread / peak_value) * 100, 1) if peak_value else 0

    if latest_change_percent is None:
        trend_label = "Stable / limited recent data"
    elif latest_change_percent >= 15:
        trend_label = "Rapid value climb"
    elif latest_change_percent >= 5:
        trend_label = "Positive momentum"
    elif latest_change_percent <= -15:
        trend_label = "Sharp value correction"
    elif latest_change_percent <= -5:
        trend_label = "Cooling market value"
    else:
        trend_label = "Mostly stable value"

    if volatility >= 65:
        volatility_label = "Very volatile"
    elif volatility >= 35:
        volatility_label = "Moderate volatility"
    else:
        volatility_label = "Stable valuation band"

    scenarios = []
    for label, multiplier in (("Bear case", 0.85), ("Base case", 1.0), ("Bull case", 1.15)):
        scenarios.append({
            "label": label,
            "value": format_money(int(current_value * multiplier)) if current_value else "-",
            "note": "15% downside" if multiplier < 1 else "Current value" if multiplier == 1 else "15% upside",
        })

    return {
        "trendLabel": trend_label,
        "volatilityLabel": volatility_label,
        "latestMove": format_money(latest_change) if latest_change is not None else "-",
        "latestMovePercent": latest_change_percent,
        "volatilityPercent": volatility,
        "currentPercentOfPeak": round((current_value / peak_value) * 100, 1) if peak_value else 0,
        "range": [
            {"label": "Lowest", "value": format_money(low_value)},
            {"label": "Current", "value": current.get("value") or format_money(current_value)},
            {"label": "Peak", "value": summary.get("peakValue") or format_money(peak_value)},
        ],
        "scenarioCards": scenarios,
    }


def build_data_quality(profile_data: dict, stats_payload: dict, injuries_payload: dict, value_payload: dict, transfers_payload: dict) -> dict:
    checks = [
        {"label": "Profile fields", "count": len([k for k, v in profile_data.items() if v]), "target": 8},
        {"label": "Stat rows", "count": len(stats_payload.get("body") or []), "target": 8},
        {"label": "Market points", "count": len(value_payload.get("result") or []), "target": 6},
        {"label": "Transfer rows", "count": len(transfers_payload.get("body") or []), "target": 2},
        {"label": "Injury rows", "count": len(injuries_payload.get("body") or []), "target": 1},
    ]
    for check in checks:
        check["complete"] = check["count"] >= check["target"]
        check["score"] = clamp_score((check["count"] / check["target"]) * 100 if check["target"] else 0)

    score = clamp_score(sum(check["score"] for check in checks) / len(checks))
    return {
        "score": score,
        "label": "Rich data profile" if score >= 75 else "Useful but partial profile" if score >= 45 else "Sparse profile",
        "checks": checks,
    }


def build_scouting_report(profile_data: dict, story: dict, stats_payload: dict, injuries_payload: dict, value_payload: dict, transfers_payload: dict) -> dict:
    stats_summary = stats_payload.get("summary") or {}
    injury_summary = injuries_payload.get("summary") or {}
    value_summary = value_payload.get("summary") or {}
    transfer_summary = transfers_payload.get("summary") or {}
    scores = story.get("scores") or {}

    strengths = []
    risks = []
    opportunities = []

    if scores.get("productivity", 0) >= 55:
        strengths.append("Strong goals + assists output relative to minutes played.")
    if stats_summary.get("appearances", 0) >= 150:
        strengths.append("Large senior sample size across competitions.")
    if scores.get("marketMomentum", 0) >= 65:
        strengths.append("Positive market-value trajectory compared with early valuation points.")
    if scores.get("availability", 0) >= 75:
        strengths.append("Availability profile is a positive signal based on listed injury downtime.")

    if injury_summary.get("totalDaysOut", 0) >= 150:
        risks.append("Injury availability needs attention because listed days out are high.")
    if value_summary.get("valueChangePercent") is not None and value_summary.get("valueChangePercent") <= -35:
        risks.append("Market value has cooled significantly from earlier valuation points.")
    if transfer_summary.get("totalTransfers", 0) >= 5:
        risks.append("High career movement may need context around role stability and fit.")
    if stats_summary.get("redCards", 0) >= 3:
        risks.append("Discipline signal should be reviewed because red-card count is elevated.")

    if not strengths:
        strengths.append("Balanced profile with enough data to support a structured review.")
    if not risks:
        risks.append("No major red flag appears from the available scraped data.")

    top_competition = stats_payload.get("topCompetition") or {}
    best_season = stats_payload.get("bestSeason") or {}
    if top_competition.get("name"):
        opportunities.append(f"Use {top_competition['name']} production as the first scouting drill-down.")
    if best_season.get("name"):
        opportunities.append(f"Review the {best_season['name']} season as the player's strongest output sample.")
    opportunities.append("Compare against a same-position player to contextualize output, availability, and market value.")

    radar = [
        {"label": "Output", "value": scores.get("productivity", 0)},
        {"label": "Availability", "value": scores.get("availability", 0)},
        {"label": "Market", "value": scores.get("marketMomentum", 0)},
        {"label": "Stability", "value": scores.get("careerStability", 0)},
        {"label": "Discipline", "value": scores.get("discipline", 0)},
    ]

    archetype = "Balanced profile"
    position = (story.get("position") or "").lower()
    if scores.get("productivity", 0) >= 70:
        archetype = "High-output attacker"
    elif "midfield" in position and stats_summary.get("assists", 0) >= stats_summary.get("goals", 0):
        archetype = "Creative midfielder"
    elif scores.get("availability", 0) >= 85 and stats_summary.get("appearances", 0) >= 150:
        archetype = "Durable regular"
    elif scores.get("marketMomentum", 0) >= 70:
        archetype = "Rising market asset"

    return {
        "archetype": archetype,
        "oneLineVerdict": f"{story.get('name')} profiles as a {archetype.lower()} with {score_label(scores.get('overall', 0)).lower()} overall data signals.",
        "strengths": strengths[:4],
        "risks": risks[:4],
        "opportunities": opportunities[:4],
        "radar": radar,
    }


def build_career_timeline(stats_payload: dict, injuries_payload: dict, value_payload: dict, transfers_payload: dict) -> list[dict]:
    events = []

    best_season = stats_payload.get("bestSeason") or {}
    if best_season.get("name"):
        events.append({
            "type": "performance",
            "label": best_season.get("name"),
            "title": "Best production season",
            "description": f"{best_season.get('goalContributions', 0)} goals + assists across {best_season.get('appearances', 0)} appearances.",
            "impact": "High",
        })

    peak_value = (value_payload.get("summary") or {}).get("peakValue")
    peak_date = (value_payload.get("summary") or {}).get("peakDate")
    if peak_value and peak_value != "-":
        events.append({
            "type": "market",
            "label": peak_date or "Market peak",
            "title": "Peak market value",
            "description": f"Reached {peak_value} in estimated market value.",
            "impact": "High",
        })

    for row in (transfers_payload.get("body") or [])[:6]:
        if len(row) >= 6:
            events.append({
                "type": "transfer",
                "label": row[0] or row[1] or "Transfer",
                "title": f"{row[2]} → {row[3]}",
                "description": f"Fee: {row[5] or '-'} • Market value: {row[4] or '-'}",
                "impact": "Medium",
            })

    for row in sorted((injuries_payload.get("body") or []), key=lambda item: number_from_text(item[4]) if len(item) > 4 else 0, reverse=True)[:4]:
        if len(row) >= 6 and number_from_text(row[4]) >= 21:
            events.append({
                "type": "injury",
                "label": row[0] or "Injury",
                "title": row[1] or "Listed injury spell",
                "description": f"{row[4]} out • {row[5]} games missed • {row[2]} to {row[3]}",
                "impact": "Review",
            })

    return events[:14]


def build_competition_profile(stats_payload: dict) -> dict:
    competitions = stats_payload.get("competitionBreakdown") or []
    total_contributions = sum(item.get("goalContributions", 0) for item in competitions) or 1
    top = []
    for item in competitions[:8]:
        top.append({
            "name": item.get("name"),
            "appearances": item.get("appearances", 0),
            "goals": item.get("goals", 0),
            "assists": item.get("assists", 0),
            "goalContributions": item.get("goalContributions", 0),
            "share": round((item.get("goalContributions", 0) / total_contributions) * 100, 1),
        })
    return {"topCompetitions": top, "totalContributionPool": total_contributions}


def analytics_payload_for_player(player_id: str) -> dict:
    player_meta = get_player_meta(player_id)
    player_meta["id"] = str(player_id)

    profile_data = scrape_profile_from_meta(player_meta)

    def safe_call(loader, fallback):
        try:
            return loader()
        except TransfermarktProxyError as exc:
            fallback["error"] = str(exc)
            return fallback
        except Exception:
            logger.exception("Analytics loader failed | player_id=%s", player_id)
            fallback["error"] = "Could not load this section right now."
            return fallback

    stats_payload = safe_call(
        lambda: build_stats_payload(player_meta, str(player_id)),
        {"header": STATS_HEADER, "body": [], "summary": {}, "seasonBreakdown": [], "competitionBreakdown": []},
    )
    injuries_payload = safe_call(
        lambda: build_injuries_payload(player_meta),
        {"header": INJURIES_HEADER, "body": [], "summary": {}},
    )
    value_payload = safe_call(
        lambda: build_value_payload(str(player_id)),
        {"result": [], "summary": {}},
    )
    transfers_payload = safe_call(
        lambda: build_transfers_payload(str(player_id)),
        {"header": TRANSFERS_HEADER, "body": [], "summary": {}},
    )

    story = build_player_story(
        profile_data,
        stats_payload,
        injuries_payload,
        value_payload,
        transfers_payload,
    )

    return {
        "profile": profile_data,
        "stats": stats_payload,
        "injuries": injuries_payload,
        "value": value_payload,
        "transfers": transfers_payload,
        "summary": story,
        "scouting": build_scouting_report(
            profile_data,
            story,
            stats_payload,
            injuries_payload,
            value_payload,
            transfers_payload,
        ),
        "timeline": build_career_timeline(stats_payload, injuries_payload, value_payload, transfers_payload),
        "valueAnalysis": build_value_analysis(value_payload),
        "competitionProfile": build_competition_profile(stats_payload),
        "dataQuality": build_data_quality(profile_data, stats_payload, injuries_payload, value_payload, transfers_payload),
    }


def compare_metric(label: str, left_value, right_value, higher_is_better=True, formatter=None) -> dict:
    left_number = left_value or 0
    right_number = right_value or 0

    if left_number == right_number:
        winner = "tie"
    elif higher_is_better:
        winner = "left" if left_number > right_number else "right"
    else:
        winner = "left" if left_number < right_number else "right"

    format_value = formatter or (lambda value: display_number(value))
    return {
        "label": label,
        "left": format_value(left_number),
        "right": format_value(right_number),
        "winner": winner,
    }


def comparison_payload(left_player_id: str, right_player_id: str) -> dict:
    left = analytics_payload_for_player(left_player_id)
    right = analytics_payload_for_player(right_player_id)

    left_stats = left.get("stats", {}).get("summary", {})
    right_stats = right.get("stats", {}).get("summary", {})
    left_injuries = left.get("injuries", {}).get("summary", {})
    right_injuries = right.get("injuries", {}).get("summary", {})
    left_value = left.get("value", {}).get("summary", {})
    right_value = right.get("value", {}).get("summary", {})
    left_transfers = left.get("transfers", {}).get("summary", {})
    right_transfers = right.get("transfers", {}).get("summary", {})

    metrics = [
        compare_metric("Appearances", left_stats.get("appearances"), right_stats.get("appearances")),
        compare_metric("Goals", left_stats.get("goals"), right_stats.get("goals")),
        compare_metric("Assists", left_stats.get("assists"), right_stats.get("assists")),
        compare_metric(
            "G+A per 90",
            left_stats.get("contributionsPer90"),
            right_stats.get("contributionsPer90"),
            True,
            lambda value: display_decimal(value),
        ),
        compare_metric(
            "Peak market value",
            left_value.get("peakValueNumber"),
            right_value.get("peakValueNumber"),
            True,
            lambda value: format_money(value) if value else "-",
        ),
        compare_metric("Days injured", left_injuries.get("totalDaysOut"), right_injuries.get("totalDaysOut"), False),
        compare_metric("Games missed", left_injuries.get("totalGamesMissed"), right_injuries.get("totalGamesMissed"), False),
        compare_metric("Transfers", left_transfers.get("totalTransfers"), right_transfers.get("totalTransfers"), False),
    ]

    return {"left": left, "right": right, "metrics": metrics}


@require_GET
def stats(request, player_id: str) -> JsonResponse:
    try:
        player_meta = get_player_meta(player_id)
        player_meta["id"] = str(player_id)
        return JsonResponse(build_stats_payload(player_meta, str(player_id)))
    except TransfermarktProxyError as exc:
        return error_response(str(exc))
    except Exception:
        logger.exception("Stats parse failed for player_id=%s", player_id)
        return error_response("Could not parse stats right now.")


@require_GET
def injuries(request, player_id: str) -> JsonResponse:
    try:
        player_meta = get_player_meta(player_id)
        player_meta["id"] = str(player_id)
        return JsonResponse(build_injuries_payload(player_meta))
    except TransfermarktProxyError as exc:
        return error_response(str(exc))
    except Exception:
        logger.exception("Injury parse failed for player_id=%s", player_id)
        return error_response("Could not parse injury history right now.")


@require_GET
def value(request, player_id: str) -> JsonResponse:
    try:
        return JsonResponse(build_value_payload(str(player_id)))
    except TransfermarktProxyError as exc:
        return error_response(str(exc))
    except Exception:
        logger.exception("Market value parse failed for player_id=%s", player_id)
        return error_response("Could not parse market value history right now.")


@require_GET
def transfers(request, player_id: str) -> JsonResponse:
    try:
        return JsonResponse(build_transfers_payload(str(player_id)))
    except TransfermarktProxyError as exc:
        return error_response(str(exc))
    except Exception:
        logger.exception("Transfer parse failed for player_id=%s", player_id)
        return error_response("Could not parse transfer history right now.")


@require_GET
def analytics(request, player_id: str) -> JsonResponse:
    try:
        return JsonResponse(analytics_payload_for_player(str(player_id)))
    except TransfermarktProxyError as exc:
        return error_response(str(exc))
    except Exception:
        logger.exception("Analytics failed for player_id=%s", player_id)
        return error_response("Could not build player analytics right now.")


@require_GET
def compare(request, left_player_id: str, right_player_id: str) -> JsonResponse:
    try:
        return JsonResponse(comparison_payload(str(left_player_id), str(right_player_id)))
    except TransfermarktProxyError as exc:
        return error_response(str(exc))
    except Exception:
        logger.exception("Compare failed for left=%s right=%s", left_player_id, right_player_id)
        return error_response("Could not compare these players right now.")
