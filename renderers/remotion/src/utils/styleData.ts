import { SegmentStyles } from "../types/segmentStyles";
import React from "react";

export function getStyleData(segmentStyles: SegmentStyles, segmentId: number) : React.CSSProperties {

    return {
        ...segmentStyles.globalStyle,
        ...(segmentStyles?.segmentStyles?.[segmentId] ?? {})
    }
}
