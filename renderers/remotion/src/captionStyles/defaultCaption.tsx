import { BaseCaptionProp } from "../types/captionProp";
import { AbsoluteFill } from "remotion";
import "./css/caption.css"

export function DefaultCaption({segment, styleData}: BaseCaptionProp) {
    return (<AbsoluteFill style={styleData} className="subtitle">
                {segment.words.map((wordData) => {
                        return <span className="word">{wordData.word}</span>
                    })}
            </AbsoluteFill>)
}