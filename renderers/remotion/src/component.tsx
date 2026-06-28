import { InputProps } from "./types/inputProps"
import { Composition } from "remotion"
import {getVideoMetadata, VideoMetadata} from '@remotion/renderer';
import { CaptionRenderer } from "./captionStyles/captionRenderer";

const fps = 30

export const RemotionRoot = () => {
    return <Composition
                component={CaptionRenderer}
                durationInFrames={300}
                fps={fps}
                width={1080}
                height={1080}
                id="main"
                
                
            />
}