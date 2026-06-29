import { InputProps } from "./types/inputProps"
import { CalculateMetadataFunction, Composition } from "remotion"
import { CaptionRenderer } from "./captionStyles/captionRenderer";
import { CaptionData } from "./types/captionData";

const fps = 30

const defaultCaptionData = {
  transcript: {
    segments: [],
    words: [],
  },
  segmentStyles: {
    captionStyle: "defaultCaption",
    globalStyle: {},
    segmentStyles: {},
  },
  videoSrc: ""
} satisfies CaptionData;

const calculateVideoMetadata: CalculateMetadataFunction<CaptionData> = 
    async ({props, defaultProps, abortSignal, isRendering}) => {

}

export const RemotionRoot = () => {
    return <Composition
                component={CaptionRenderer}
                durationInFrames={300}
                fps={fps}
                width={1080}
                height={1080}
                id="main"
                defaultProps={defaultCaptionData}
                calculateMetadata={calculateVideoMetadata}
            />
}