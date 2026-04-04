import React, { useEffect, useRef, useState } from "react";
import { Button, Card, CardBody, Chip, Input, Spinner } from "@nextui-org/react";
import { fetchJson } from "../lib/api";

export default function Bar({ onSearch, isSearching }) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [searchError, setSearchError] = useState("");
  const barRef = useRef(null);

  useEffect(() => {
    if (isSearching) {
      setShowSuggestions(false);
      setSuggestions([]);
    }
  }, [isSearching]);

  useEffect(() => {
    const trimmedQuery = query.trim();

    if (trimmedQuery.length < 2 || isSearching) {
      setSuggestions([]);
      setShowSuggestions(false);
      setIsLoadingSuggestions(false);
      return undefined;
    }

    const controller = new AbortController();

    const timeoutId = window.setTimeout(async () => {
      try {
        setIsLoadingSuggestions(true);
        const payload = await fetchJson(`search/${encodeURIComponent(trimmedQuery)}`, {
          signal: controller.signal,
        });
        setSuggestions(payload.results || []);
        setShowSuggestions(true);
      } catch (error) {
        if (error.name !== "AbortError") {
          setSuggestions([]);
          setShowSuggestions(false);
        }
      } finally {
        setIsLoadingSuggestions(false);
      }
    }, 250);

    return () => {
      controller.abort();
      window.clearTimeout(timeoutId);
    };
  }, [query, isSearching]);

  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (barRef.current && !barRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  const submitSearch = (player = null) => {
    const selected =
      player ||
      (showSuggestions && suggestions.length ? suggestions[0] : null);

    const trimmedValue = (selected?.name || query).trim();

    if (!trimmedValue) {
      setSearchError("Enter a player name first.");
      return;
    }

    setSearchError("");
    setShowSuggestions(false);
    setSuggestions([]);

    onSearch({
      id: selected?.id || null,
      name: selected?.name || trimmedValue,
      query: trimmedValue,
    });
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      submitSearch();
    }
  };

  const handleSuggestionClick = (player) => {
    setQuery(player.name);
    submitSearch(player);
  };

  return (
    <div className="search-panel" ref={barRef}>
      <div className="bar">
        <Input
          type="search"
          size="lg"
          radius="lg"
          placeholder="Search a player... e.g. Marcus Rashford"
          className="search-bar"
          value={query}
          onValueChange={setQuery}
          onKeyDown={handleKeyDown}
          isClearable
          onClear={() => {
            setQuery("");
            setSuggestions([]);
            setShowSuggestions(false);
            setSearchError("");
          }}
        />

        <Button
          className="search-button"
          onClick={() => submitSearch()}
          color="primary"
          variant="solid"
          isLoading={isSearching}
          isDisabled={!query.trim()}
        >
          Search
        </Button>
      </div>

      {searchError && <p className="error-copy">{searchError}</p>}

      {showSuggestions && !isSearching && (
        <Card className="suggestions-card">
          <CardBody>
            {isLoadingSuggestions ? (
              <div className="suggestions-loading">
                <Spinner size="sm" />
                <span>Finding players...</span>
              </div>
            ) : suggestions.length ? (
              <div className="suggestions-list">
                {suggestions.map((player) => (
                  <button
                    key={`${player.id}-${player.name}`}
                    type="button"
                    className="suggestion-item"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => handleSuggestionClick(player)}
                  >
                    <div>
                      <div className="suggestion-name">{player.name}</div>
                      <div className="suggestion-meta">
                        {[player.club, player.position, player.age ? `${player.age}` : null]
                          .filter(Boolean)
                          .join(" • ")}
                      </div>
                    </div>
                    {player.marketValue && (
                      <Chip size="sm" variant="flat">
                        {player.marketValue}
                      </Chip>
                    )}
                  </button>
                ))}
              </div>
            ) : (
              <div className="suggestions-empty">No players found.</div>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
}