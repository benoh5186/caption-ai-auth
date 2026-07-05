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
        const enterWord = interpolate(videoCurrentTime, [wordData.start, wordData.end], [0, 1], {extrapolateLeft: "clamp", "extrapolateRight" : "clamp"})
        const exitWord = interpolate(videoCurrentTime, [wordData.start, wordData.end], [1, 0], {extrapolateLeft: "clamp", "extrapolateRight" : "clamp"})
        const wordTransition = Math.min(enterWord, exitWord)
        const color = interpolateColors(wordTransition, [0, 1], [styleData.backgroundColor as string, getCurrentWordStyle(styleData.backgroundColor as string).backgroundColor])
        return color 
    }

    return (
        <div
            style={styleData}
            className="subtitle"
        > 
            {segment?.words.map((wordData) => {
                const colorFetch = getCurrentWordColor(wordData)
                const color = typeof colorFetch === "string" ? colorFetch : getCurrentWordStyle(styleData.backgroundColor as string).backgroundColor
                if (wordData.start <= videoCurrentTime && wordData.end >= videoCurrentTime) {
                    return <span className="word active" style={{backgroundColor : color}}>{wordData.word}</span>
                } else {
                    return <span className="word">{wordData.word}</span>
                }
            })}
        </div>
    )
}

function getCurrentWordStyle(color: string) {
    const backgroundColor = getContrastColor(color)

    return {
        backgroundColor: backgroundColor
    }
}

function getContrastColor(hexColor: string) {
    const hex = hexColor.replace("#", "");

    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);

    const brightness = (r * 299 + g * 587 + b * 114) / 1000;

    return brightness > 128 ? "#000000" : "#ffffff";
}