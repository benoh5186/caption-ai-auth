import { Transcript } from "./transcript";
import { SegmentStyles } from "./segmentStyles";

export type CaptionData = {
    transcript: Transcript,
    segmentStyles: SegmentStyles,
    videoSrc: string 
}