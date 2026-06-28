import { TimedCaptionProp } from "../types/captionProp";
import { AbsoluteFill } from "remotion";

export function KineticWordCaption({segment, styleData, videoCurrentTime}: TimedCaptionProp) {
    return (
        <AbsoluteFill
            style={styleData}
        > 
            {segment?.words.map((wordData) => {
                if (wordData.start <= videoCurrentTime && wordData.end >= videoCurrentTime) {
                    return <span className="word active">{wordData.word}</span>
                } else {
                    return <span className="word">{wordData.word}</span>
                }
            })}
        </AbsoluteFill>
    )
}