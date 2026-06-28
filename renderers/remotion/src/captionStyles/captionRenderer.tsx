import { CaptionData } from "../types/captionData";
import { Segment } from "../types/transcript";
import { SegmentStyles } from "../types/segmentStyles";
import { useVideoConfig, useCurrentFrame, AbsoluteFill } from "remotion";
import { getStyleData } from "../utils/styleData";
import { KineticWordCaption } from "./kineticCaption";
import { DefaultCaption } from "./defaultCaption";
import { OffthreadVideo } from "remotion";


export function CaptionRenderer({transcript, segmentStyles, videoSrc}: CaptionData) {
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
    const captionComponent = getCaptionComponent(currentSegment, styleData, segmentStyles, videoCurrentTime)
    return (
        <AbsoluteFill>
            <AbsoluteFill>
                <OffthreadVideo src={videoSrc} />
            </AbsoluteFill>
            <AbsoluteFill>
                {captionComponent}
            </AbsoluteFill>
        </AbsoluteFill>
    )
}

function getCaptionComponent(segment: Segment, styleData: Record<string, unknown>, segmentStyles: SegmentStyles, videoCurrentTime: number) {
    switch (segmentStyles.captionStyle) {
        case "kineticWordCaption" :
            return <KineticWordCaption
                        segment={segment}
                        styleData={styleData}
                        videoCurrentTime={videoCurrentTime}/> 
        case "defaultCaption" :
            return <DefaultCaption 
                        segment={segment}
                        styleData={styleData}/> 
        default:
            return <DefaultCaption 
                        segment={segment}
                        styleData={styleData}/> 
    }
}