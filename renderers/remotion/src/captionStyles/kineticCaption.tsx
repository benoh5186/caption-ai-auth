import { CaptionProp } from "../types/captionProp";
import React from "react";
import { Easing, interpolate, interpolateColors,useCurrentFrame, useVideoConfig } from "remotion";
import { getStyleData } from "../utils/styleData";
import "./css/caption.css"
import "./css/kineticCaption.css"
import { Word } from "../types/transcript";

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
    
    function getCurrentWordColor(wordData: Word): string | null {
        if (wordData.end <= wordData.start) return null 
        const wordTransition = interpolate(videoCurrentTime, [wordData.start, wordData.end], [0, 1], {extrapolateLeft: "clamp", "extrapolateRight" : "clamp"})
        const color = interpolateColors(wordTransition, [0, 1], [withOpacity(styleData.backgroundColor as string, 0), styleData.backgroundColor as string])
        return color 
    }

    return (
        <div
            style={{...styleData, backgroundColor: "transparent"}}
            className="subtitle"
        > 
            {segment?.words.map((wordData) => {
                const colorFetch = getCurrentWordColor(wordData)
                const color = typeof colorFetch === "string" ? colorFetch : styleData.backgroundColor as string
                if (wordData.start <= videoCurrentTime && wordData.end >= videoCurrentTime) {
                    return <span className="word active" style={{backgroundColor : color}}>{wordData.word}</span>
                } else {
                    return <span className="word">{wordData.word}</span>
                }
            })}
        </div>
    )
}

function withOpacity(color: string, opacity: number): string {
    const hex = color.replace("#", "").slice(0, 6);
    const alpha = Math.round(opacity * 255).toString(16).padStart(2, "0")
    return `#${hex}${alpha}`

}
