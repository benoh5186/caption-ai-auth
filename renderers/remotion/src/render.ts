import {resolve} from "node:path";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { RenderRequest } from "./types/renderRequest";


const readStdin = async (): Promise<string> => {
    let data = ""
    process.stdin.setEncoding("utf8")
    for await (const chunk of process.stdin) {
        data += chunk 
    }
    return data 
}

const main = async () => {
    const request: RenderRequest = JSON.parse(await readStdin())

    const serveUrl = resolve(__dirname, "..", "dist/remotion-bundle")
    const composition = await selectComposition(
        {
            serveUrl: serveUrl,
            id: "main",
            inputProps: request.inputProps
        }
    )

    await renderMedia({
        composition: composition,
        serveUrl: serveUrl,
        codec: 'h264',
        outputLocation: request.outputLocation,
        inputProps: request.inputProps
    })
}

main().catch((err) => {
    console.log(err)
    process.exitCode = 1
})