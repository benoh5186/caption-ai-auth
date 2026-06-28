import { CaptionProp } from "../types/captionProp";
import { AbsoluteFill } from "remotion";
import { useVideoConfig, useCurrentFrame } from "remotion";
import { getStyleData } from "../utils/styleData";

export function KineticWordCaption({transcript, segmentStyles}: CaptionProp) {
    const {fps} = useVideoConfig()
    const frame = useCurrentFrame()
    const videoCurrentTime = frame / fps 
    const currentSegment = transcript?.segments.find((segment) => {
        return segment.start <= videoCurrentTime && segment.end >= videoCurrentTime
    })
    const styleData = getStyleData(segmentStyles, currentSegment?.id)

    return (
        <AbsoluteFill
            style={styleData}
        > 
            {currentSegment?.words.map((wordData) => {
                if (wordData.start >= videoCurrentTime && wordData.end <= videoCurrentTime) {
                    return <span className="word active">{wordData.word}</span>
                } else {
                    return <span className="word">{wordData.word}</span>
                }
            })}
        </AbsoluteFill>
    )
}