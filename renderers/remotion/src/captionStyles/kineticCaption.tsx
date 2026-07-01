import { TimedCaptionProp } from "../types/captionProp";
import { AbsoluteFill } from "remotion";
import "./css/caption.css"
import "./css/kineticCaption.css"

export function KineticWordCaption({segment, styleData, videoCurrentTime}: TimedCaptionProp) {
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