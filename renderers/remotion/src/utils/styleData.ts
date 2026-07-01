import { SegmentStyles } from "../types/segmentStyles";

export function getStyleData(segmentStyles: SegmentStyles, segmentId: number) : Record<string, string | number> {

    return {
        ...segmentStyles.globalStyle,
        ...(segmentStyles?.segmentStyles?.[segmentId] ?? {})
    }
}
