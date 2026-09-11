from __future__ import annotations

import csv
import io
from typing import Any

from mijobs.domain import MappingRelation, TaxonomyMappingInput
from mijobs.sources.base import FetchedArtifact, SourceFetchError


class CIPSOC2020CrosswalkParser:
    """Parser for the official NCES/BLS CIP 2020 -> SOC 2018 crosswalk.

    A crosswalk edge is a documented relationship, not a probability and not proof that
    every graduate enters the linked occupation. Therefore edges default to RELATED and
    carry no synthetic weight.
    """

    parser_version = "nces-cip2020-soc2018/1"

    def normalize(
        self,
        artifact: FetchedArtifact,
        *,
        cip_field: str = "CIP2020Code",
        cip_title_field: str = "CIP2020Title",
        soc_field: str = "SOC2018Code",
        soc_title_field: str = "SOC2018Title",
    ) -> list[TaxonomyMappingInput]:
        rows = _delimited_rows(artifact.content)
        required = {cip_field, soc_field}
        if not rows:
            raise SourceFetchError("CIP-SOC crosswalk contains no rows")
        missing = required - set(rows[0])
        if missing:
            raise SourceFetchError(f"CIP-SOC crosswalk missing required fields: {sorted(missing)}")

        mappings: list[TaxonomyMappingInput] = []
        seen: set[tuple[str, str]] = set()
        for row in rows:
            cip = row[cip_field].strip()
            soc = row[soc_field].strip()
            if not cip or not soc:
                continue
            pair = (cip, soc)
            if pair in seen:
                continue
            seen.add(pair)
            metadata: dict[str, Any] = {
                "crosswalk": "CIP 2020 to SOC 2018",
                "source_locator": artifact.locator,
                "parser_version": self.parser_version,
            }
            if cip_title_field in row:
                metadata["cip_title"] = row[cip_title_field].strip()
            if soc_title_field in row:
                metadata["soc_title"] = row[soc_title_field].strip()
            mappings.append(
                TaxonomyMappingInput(
                    mapping_key=f"cip2020:{cip}:soc2018:{soc}",
                    from_system="CIP",
                    from_version="2020",
                    from_code=cip,
                    to_system="SOC",
                    to_version="2018",
                    to_code=soc,
                    relation=MappingRelation.RELATED,
                    weight=None,
                    metadata=metadata,
                )
            )
        return mappings


def _delimited_rows(content: bytes) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1252")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if reader.fieldnames is None:
        raise SourceFetchError("CIP-SOC crosswalk has no header")
    rows: list[dict[str, str]] = []
    for row in reader:
        normalized: dict[str, str] = {}
        for key, value in row.items():
            if key is None or isinstance(value, list):
                raise SourceFetchError("CIP-SOC row does not match its header width")
            normalized[str(key)] = value or ""
        rows.append(normalized)
    return rows
