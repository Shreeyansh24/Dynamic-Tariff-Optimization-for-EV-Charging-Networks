"""Load and convert ACN-Data (Adaptive Charging Network) sessions."""

from __future__ import annotations

import gzip
import io
import json
import re
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from config import ACN_API_BASE, ACN_SITES, DATA_RAW

ACN_STATIC_BASE = (
    "https://raw.githubusercontent.com/tongxin-li/ACN-Data-Static/main"
    "/time%20series%20data"
)
ACN_STATIC_GARAGES = {
    "caltech": ["caltech/California_Garage_01", "caltech/N_Wilson_Garage_01"],
    "jpl": ["jpl/Arroyo_Garage_01"],
}


def _parse_acn_datetime(value: str | None) -> pd.Timestamp | pd.NaT:
    if not value:
        return pd.NaT
    try:
        return pd.Timestamp(parsedate_to_datetime(value))
    except (TypeError, ValueError, OverflowError):
        return pd.NaT


def _session_duration_hours(row: pd.Series) -> float:
    start = row.get("connectionTime")
    end = row.get("disconnectTime")
    if pd.isna(start) or pd.isna(end):
        return 0.0
    delta = (end - start).total_seconds() / 3600.0
    return max(delta, 0.0)


def _parse_static_filename(filename: str) -> dict[str, str]:
    """Extract station and session id from static ACN filename."""
    base = filename.replace(".csv.gz", "")
    match = re.match(
        r"(?P<station>.+)-(?P<date>\d{4}-\d{2}-\d{2}T[\d-]+)$",
        base,
    )
    if match:
        return {
            "station_id": match.group("station"),
            "session_id": base,
        }
    return {"station_id": base, "session_id": base}


def _parse_timeseries_gz(content: bytes, meta: dict[str, str], site_id: str) -> dict[str, Any] | None:
    """Convert one gzipped ACN time-series file into a session record."""
    try:
        text = gzip.decompress(content).decode("utf-8")
        df = pd.read_csv(io.StringIO(text))
        if df.empty:
            return None

        ts_col = df.columns[0]
        df[ts_col] = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
        df = df.dropna(subset=[ts_col])
        if df.empty:
            return None

        energy_col = next(
            (c for c in df.columns if "energy" in c.lower() and "kwh" in c.lower()),
            None,
        )
        kwh = float(df[energy_col].max()) if energy_col else 0.0
        if kwh <= 0:
            return None

        start = df[ts_col].iloc[0]
        end = df[ts_col].iloc[-1]
        duration_hr = max((end - start).total_seconds() / 3600.0, 0.01)

        return {
            "dataset": "ACN",
            "site_id": site_id,
            "station_id": meta["station_id"],
            "space_id": None,
            "cluster_id": None,
            "session_id": meta["session_id"],
            "user_id": None,
            "connection_time": start,
            "disconnect_time": end,
            "done_charging_time": end,
            "kwh_delivered": kwh,
            "timezone": "US/Pacific",
            "session_duration_hr": duration_hr,
        }
    except (OSError, ValueError, KeyError, pd.errors.ParserError):
        return None


def download_acn_static(
    max_files_per_garage: int = 800,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Download ACN sessions from public static time-series repository."""
    output_dir = output_dir or (DATA_RAW / "acn")
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: dict[str, Path] = {}

    for site_id, garages in ACN_STATIC_GARAGES.items():
        sessions: list[dict[str, Any]] = []
        for garage_path in garages:
            api_url = (
                "https://api.github.com/repos/tongxin-li/ACN-Data-Static/contents/"
                f"time%20series%20data/{garage_path}?ref=main"
            )
            try:
                resp = requests.get(api_url, timeout=60)
                resp.raise_for_status()
                files = [
                    f for f in resp.json()
                    if f["name"].endswith(".csv.gz")
                ][:max_files_per_garage]
            except requests.RequestException as exc:
                print(f"[ACN-Static] Failed listing {garage_path}: {exc}")
                continue

            for i, file_info in enumerate(files):
                try:
                    dl = requests.get(file_info["download_url"], timeout=60)
                    dl.raise_for_status()
                    meta = _parse_static_filename(file_info["name"])
                    record = _parse_timeseries_gz(dl.content, meta, site_id)
                    if record:
                        sessions.append(record)
                except requests.RequestException:
                    continue
                if (i + 1) % 200 == 0:
                    print(f"[ACN-Static] {garage_path}: {i + 1} files processed")

        out_path = output_dir / f"{site_id}_sessions.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(sessions, f, default=str)
        saved[site_id] = out_path
        print(f"[ACN-Static] Saved {len(sessions)} sessions for {site_id}")

    return saved


def download_acn_data(
    sites: list[str] | None = None,
    max_pages_per_site: int = 200,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    """Paginate ACN-Data API and save per-site JSON files."""
    sites = sites or ACN_SITES
    output_dir = output_dir or (DATA_RAW / "acn")
    output_dir.mkdir(parents=True, exist_ok=True)

    saved: dict[str, Path] = {}
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    api_ok = False
    for site in sites:
        all_sessions: list[dict[str, Any]] = []
        url: str | None = f"{ACN_API_BASE}/{site}?pretty"
        page = 0

        while url and page < max_pages_per_site:
            page += 1
            try:
                resp = session.get(url, timeout=60)
                resp.raise_for_status()
                payload = resp.json()
            except requests.RequestException as exc:
                print(f"[ACN] {site} page {page} failed: {exc}")
                break

            sessions = payload.get("_items", [])
            if not sessions:
                break
            all_sessions.extend(sessions)
            api_ok = True

            links = payload.get("_links", {})
            next_href = links.get("next", {}).get("href")
            url = f"https://ev.caltech.edu/api/v1/{next_href}" if next_href else None
            time.sleep(0.2)

        out_path = output_dir / f"{site}_sessions.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_sessions, f)
        saved[site] = out_path
        print(f"[ACN] Saved {len(all_sessions)} sessions for {site} -> {out_path}")

    if not api_ok or all(len(json.load(open(p))) == 0 for p in saved.values()):
        print("[ACN] API unavailable — falling back to static time-series repository...")
        saved = download_acn_static(output_dir=output_dir)

    return saved


def load_acn_sessions(
    json_paths: list[Path] | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    """Convert ACN JSON session files to a normalized CSV dataframe."""
    json_paths = json_paths or list((DATA_RAW / "acn").glob("*_sessions.json"))
    if not json_paths:
        raise FileNotFoundError(
            "No ACN JSON files found. Run download_acn_data() first."
        )

    records: list[dict[str, Any]] = []
    for path in json_paths:
        with open(path, encoding="utf-8") as f:
            sessions = json.load(f)

        for s in sessions:
            if "connection_time" in s:
                records.append(s)
            else:
                records.append(
                    {
                        "dataset": "ACN",
                        "site_id": s.get("siteID"),
                        "station_id": s.get("stationID"),
                        "space_id": s.get("spaceID"),
                        "cluster_id": s.get("clusterID"),
                        "session_id": s.get("sessionID"),
                        "user_id": s.get("userID"),
                        "connection_time": _parse_acn_datetime(s.get("connectionTime")),
                        "disconnect_time": _parse_acn_datetime(s.get("disconnectTime")),
                        "done_charging_time": _parse_acn_datetime(s.get("doneChargingTime")),
                        "kwh_delivered": float(s.get("kWhDelivered") or 0.0),
                        "timezone": s.get("timezone"),
                    }
                )

    df = pd.DataFrame(records)
    if "session_duration_hr" not in df.columns:
        df["session_duration_hr"] = df.apply(_session_duration_hours, axis=1)
    df["connection_time"] = pd.to_datetime(df["connection_time"], utc=True)
    df["disconnect_time"] = pd.to_datetime(df["disconnect_time"], utc=True, errors="coerce")
    df = df.dropna(subset=["connection_time"])
    df = df.sort_values("connection_time").reset_index(drop=True)

    if output_csv:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False)

    return df
