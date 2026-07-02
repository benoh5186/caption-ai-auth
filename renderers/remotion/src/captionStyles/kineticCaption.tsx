import { CaptionProp } from "../types/captionProp";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { getStyleData } from "../utils/styleData";
import "./css/caption.css"
import "./css/kineticCaption.css"

export function KineticWordCaption({transcript, segmentStyles}: CaptionProp) {
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

    return (
        <AbsoluteFill
            style={styleData}
            className="subtitle"
        > 
            {segment?.words.map((wordData) => {
                if (wordData.start <= videoCurrentTime && wordData.end >= videoCurrentTime) {
                    return <span className="word active" style={getCurrentWordStyle(styleData.backgroundColor)}>{wordData.word}</span>
                } else {
                    return <span className="word">{wordData.word}</span>
                }
            })}
        </AbsoluteFill>
    )
}

function getCurrentWordStyle(segmentStyle: string | number) {
    const backgroundColor = getContrastColor(segmentStyle)

    return {
        backgroundColor: backgroundColor
    }
}

function getContrastColor(hexColor: string | number) {
    if (typeof hexColor === "number") {
        return "#000000"
    }
    const hex = hexColor.replace("#", "");

    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);

    const brightness = (r * 299 + g * 587 + b * 114) / 1000;

    return brightness > 128 ? "#000000" : "#ffffff";
}