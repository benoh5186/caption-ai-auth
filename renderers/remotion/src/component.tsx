import { CalculateMetadataFunction, Composition } from "remotion"
import { getMediaMetadata } from "./utils/mediaMetadata";
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
    async ({props}) => {
        const {durationInSeconds, displayWidth, displayHeight} = await getMediaMetadata(props.videoSrc)
        const durationInFrames = Math.ceil(durationInSeconds * fps)
        return {
            durationInFrames: durationInFrames,
            width: displayWidth,
            height: displayHeight
        }
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