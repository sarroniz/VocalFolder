# app/core/textgrid_parser.py

from textgrid import TextGrid

def extract_intervals(textgrid_path, tier_name=None):
    tg = TextGrid.fromFile(textgrid_path)

    # If no tier name provided or not found, use first IntervalTier
    tier = None
    if tier_name:
        tier = tg.getFirst(tier_name)
    else:
        for t in tg.tiers:
            if t.__class__.__name__ == "IntervalTier":
                tier = t
                break

    if tier is None:
        raise ValueError(f"No IntervalTier found in {textgrid_path}")

    intervals = []
    for interval in tier:
        if interval.mark.strip():
            intervals.append({
                'label': interval.mark,
                'start': interval.minTime,
                'end': interval.maxTime,
                'duration': interval.maxTime - interval.minTime
            })
    return intervals