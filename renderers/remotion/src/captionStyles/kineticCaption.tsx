import { CaptionProp } from "../types/captionProp";
import { AbsoluteFill } from "remotion";
import { useVideoConfig, useCurrentFrame } from "remotion";
import { getStyleData } from "../utils/styleData";

export function KineticWordCaption({transcript, segmentStyles}: CaptionProp) {
    const {fps, durationInFrames} = useVideoConfig()
    const frame = useCurrentFrame()
    const videoLength = durationInFrames / fps 
    const videoCurrentTime = frame / fps 
    const currentSegment = transcript?.segments.find((segment) => {
        return segment.start <= videoCurrentTime && segment.end >= videoCurrentTime
    })
    const styleData = getStyleData(segmentStyles, currentSegment?.id)


}