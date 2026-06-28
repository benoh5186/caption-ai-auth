import { Segment } from "./transcript"

export type CaptionProp = {
    segment: Segment,
    styleData: Record<string, unknown>
    videoCurrentTime: number 
}