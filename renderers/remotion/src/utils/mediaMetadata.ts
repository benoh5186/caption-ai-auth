import {Input, ALL_FORMATS, UrlSource} from "mediabunny"


export const getMediaMetadata = async (src: string) => {
    const input = new Input({
        formats: ALL_FORMATS,
        source: new UrlSource(src)
    })

    const durationInSeconds = await input.computeDuration();
    const videoTrack = await input.getPrimaryVideoTrack();

    const displayWidth = await videoTrack?.getDisplayWidth();
    const displayHeight = await videoTrack?.getDisplayHeight();

    return {
        durationInSeconds,
        displayWidth,
        displayHeight
    }
}