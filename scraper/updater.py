from datetime import datetime
from loguru import logger
from scraper.models import HotelDataParsed, HotelRecord, TRACKED_FIELDS


class RecordUpdater:
    """Compares fresh parsed snapshots against stored records and produces updates."""

    def process(
        self,
        fresh: list[HotelDataParsed],
        records: list[HotelRecord],
        update_mode: bool,
    ) -> tuple[list[HotelRecord], list[HotelRecord], list[HotelRecord]]:
        """Process fresh snapshots against existing records.

        In both modes, new hotels are always added.
        In update_mode=True, existing hotels are also checked for field changes.

        Returns:
            all_records    — full updated list to save to disk
            new_records    — hotels seen for the first time
            changed_records — existing hotels where at least one field changed
        """
        today = datetime.now().strftime("%d.%m.%Y")
        index: dict[str, HotelRecord] = {r.id: r for r in records}
        new_records: list[HotelRecord] = []
        changed_records: list[HotelRecord] = []

        for parsed in fresh:
            if parsed.id not in index:
                record = HotelRecord.from_parsed(parsed)
                index[parsed.id] = record
                new_records.append(record)
                logger.debug(f"NEW hotel: {parsed.id}")
            elif update_mode:
                record = index[parsed.id]
                if self._apply_changes(record, parsed, today):
                    changed_records.append(record)

        if update_mode:
            logger.info(
                f"Update complete — new: {len(new_records)}, changed: {len(changed_records)}"
            )
        else:
            logger.info(f"Scan complete — new hotels found: {len(new_records)}")

        return list(index.values()), new_records, changed_records

    def _apply_changes(
        self, record: HotelRecord, parsed: HotelDataParsed, today: str
    ) -> bool:
        """Write new date-keyed entries for any fields that differ from the latest stored value.

        Returns True if at least one field was updated.
        """
        changed = False
        for field_name in TRACKED_FIELDS:
            new_val = getattr(parsed, field_name)
            current_val = record.latest(field_name)
            if new_val != current_val:
                history: dict = getattr(record, field_name)
                history[today] = new_val
                logger.debug(
                    f"CHANGED [{field_name}] for {record.id}: {current_val!r} → {new_val!r}"
                )
                changed = True
        return changed
