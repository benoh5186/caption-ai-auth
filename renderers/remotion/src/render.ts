import {resolve} from "node:path";
import {bundle} from "@remotion/bundler";
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

const request: RenderRequest = JSON.parse(await readStdin())

const bundled = await bundle({entryPoint: resolve("./src/index.ts")})
const composition = await selectComposition(
    {
        serveUrl: bundled,
        id: "main",
        inputProps: request.inputProps
    }
)

await renderMedia({
    composition: composition,
    serveUrl: bundled,
    codec: 'h264',
    outputLocation: request.outputLocation,
    inputProps: request.inputProps
})