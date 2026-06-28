import { Segment } from "./transcript"

export type BaseCaptionProp = {
    segment: Segment,
    styleData: Record<string, unknown>
}

export type TimedCaptionProp = BaseCaptionProp & {
    videoCurrentTime: number
}
