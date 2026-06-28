import { BaseCaptionProp } from "../types/captionProp";
import { AbsoluteFill } from "remotion";

export function DefaultCaption({segment, styleData}: BaseCaptionProp) {
    return (<AbsoluteFill style={styleData}>
                {segment.words.map((wordData) => {
                        return <span className="word">{wordData.word}</span>
                    })}
            </AbsoluteFill>)
}