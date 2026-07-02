import { CaptionData } from "../types/captionData";
import { Segment, Transcript } from "../types/transcript";
import { SegmentStyles } from "../types/segmentStyles";
import { useVideoConfig, useCurrentFrame, AbsoluteFill } from "remotion";
import { getStyleData } from "../utils/styleData";
import { KineticWordCaption } from "./kineticCaption";
import { DefaultCaption } from "./defaultCaption";
import { OffthreadVideo } from "remotion";


export function CaptionRenderer({transcript, segmentStyles, videoSrc}: CaptionData) {
    const captionComponent = getCaptionComponent(transcript, segmentStyles)
    return (
        <AbsoluteFill>
            <AbsoluteFill>
                <OffthreadVideo src={videoSrc} />
            </AbsoluteFill>
            {captionComponent}
        </AbsoluteFill>
    )
}

function getCaptionComponent(transcript: Transcript, segmentStyles: SegmentStyles) {
    switch (segmentStyles.captionStyle) {
        case "kineticWordCaption" :
            return <KineticWordCaption
                        transcript={transcript}
                        segmentStyles={segmentStyles}/> 
        case "defaultCaption" :
            return <DefaultCaption 
                        transcript={transcript}
                        segmentStyles={segmentStyles}/> 
        default:
            return <DefaultCaption 
                        transcript={transcript}
                        segmentStyles={segmentStyles}/> 
    }
}