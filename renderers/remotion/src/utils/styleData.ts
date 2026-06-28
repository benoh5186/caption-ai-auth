import { SegmentStyles } from "../types/segmentStyles";

export function getStyleData(segmentStyles: SegmentStyles, segmentId?: number) {

    return {
        ...segmentStyles.globalStyle,
        ...(segmentStyles ?? {}),
        ...(segmentId === undefined ? {} : segmentStyles?.segmentStyles?.[segmentId] ?? {})
    }
}
