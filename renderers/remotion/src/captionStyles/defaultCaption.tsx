import { CaptionProp } from "../types/captionProp";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import "./css/caption.css"
import { getStyleData } from "../utils/styleData";

export function DefaultCaption({transcript, segmentStyles}: CaptionProp) {
    const {fps} = useVideoConfig()
    const frame = useCurrentFrame()
    const videoCurrentTime = frame / fps
    const segment = transcript?.segments.find((seg) => {
        return seg.start <= videoCurrentTime && seg.end >= videoCurrentTime
    })
    if (!segment) {
        return null 
    }
    const styleData = getStyleData(segmentStyles, segment.id)

    return (<div style={styleData} className="subtitle">
                {segment.words.map((wordData) => {
                        return <span className="word">{wordData.word}</span>
                    })}
            </div>)
}