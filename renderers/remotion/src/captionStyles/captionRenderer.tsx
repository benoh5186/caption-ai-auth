import { CaptionData } from "../types/captionData";
import { Segment } from "../types/transcript";
import { SegmentStyles } from "../types/segmentStyles";
import { useVideoConfig, useCurrentFrame } from "remotion";
import { getStyleData } from "../utils/styleData";
import { KineticWordCaption } from "./kineticCaption";


export function CaptionRenderer({transcript, segmentStyles}: CaptionData) {
    const {fps} = useVideoConfig()
    const frame = useCurrentFrame()
    const videoCurrentTime = frame / fps
    const currentSegment = transcript?.segments.find((segment) => {
        return segment.start <= videoCurrentTime && segment.end >= videoCurrentTime
    })
    if (!currentSegment) {
        return null 
    }
    const styleData = getStyleData(segmentStyles, currentSegment.id)
    return getCaptionComponent(currentSegment, styleData, segmentStyles, videoCurrentTime)
}

function getCaptionComponent(segment: Segment, styleData: Record<string, unknown>, segmentStyles: SegmentStyles, videoCurrentTime: number) {
    switch (segmentStyles.captionStyle) {
        case "kineticWordCaption" :
            return <KineticWordCaption
                        segment={segment}
                        styleData={styleData}
                        videoCurrentTime={videoCurrentTime}/> 
        case "defaultCaption" :
            return 
        default:
            return 
    }
}