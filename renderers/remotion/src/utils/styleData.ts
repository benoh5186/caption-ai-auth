import { SegmentStyles } from "../types/segmentStyles";

export function getStyleData(segmentStyles: SegmentStyles, segmentId?: number) {

    return {
        ...segmentStyles.globalStyle,
        ...(segmentId === undefined ? {} : segmentStyles?.segmentStyles?.[segmentId] ?? {})
    }
}
