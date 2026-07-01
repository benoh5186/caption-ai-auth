import { Segment } from "./transcript"

export type BaseCaptionProp = {
    segment: Segment,
    styleData: Record<string, number | string >
}

export type TimedCaptionProp = BaseCaptionProp & {
    videoCurrentTime: number
}
