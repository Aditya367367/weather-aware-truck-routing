import { useEffect, useId, useState } from "react";
import { api } from "../api/client";
import type { Place } from "../api/types";
import { useDebounced } from "../hooks/useDebounced";

interface Props {
  label: string;
  value: Place | null;
  onChange: (place: Place | null) => void;
}

/** Type-ahead place picker. A place only counts once the user has chosen a suggestion. */
export function PlaceInput({ label, value, onChange }: Props) {
  const id = useId();
  const [text, setText] = useState(value?.label ?? "");
  const [options, setOptions] = useState<Place[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const query = useDebounced(text.trim(), 300);

  useEffect(() => {
    if (value) setText(value.label); // external updates (e.g. swap)
  }, [value]);

  useEffect(() => {
    if (query.length < 3 || value?.label === query) {
      setOptions([]);
      return;
    }
    const c = new AbortController();
    api
      .geocode(query, c.signal)
      .then((r) => {
        setOptions(r);
        setActive(0);
      })
      .catch(() => {}); // aborted or offline: keep the field usable
    return () => c.abort();
  }, [query, value]);

  const choose = (p: Place) => {
    onChange(p);
    setText(p.label);
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open || !options.length) return;
    if (e.key === "ArrowDown") (e.preventDefault(), setActive((a) => (a + 1) % options.length));
    else if (e.key === "ArrowUp") (e.preventDefault(), setActive((a) => (a - 1 + options.length) % options.length));
    else if (e.key === "Enter") (e.preventDefault(), choose(options[active]));
    else if (e.key === "Escape") setOpen(false);
  };

  return (
    <div className="field place">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        role="combobox"
        aria-expanded={open && options.length > 0}
        aria-controls={`${id}-list`}
        aria-autocomplete="list"
        autoComplete="off"
        placeholder="City, address or place"
        value={text}
        aria-invalid={!value && text.length > 0}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          if (value) onChange(null);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
      />
      {open && options.length > 0 && (
        <ul className="suggestions" id={`${id}-list`} role="listbox">
          {options.map((o, i) => (
            <li
              key={`${o.lat},${o.lng}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? "active" : undefined}
              onMouseDown={() => choose(o)}
            >
              {o.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
