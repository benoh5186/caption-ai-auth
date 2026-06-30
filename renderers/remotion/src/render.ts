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

const isObj = (value: unknown): value is Record<string, unknown> => {
    return typeof value === "object" && value !== null
}

const isRenderRequest = (request: unknown): request is RenderRequest => {
    if (!isObj(request)) return false 
    return (isObj(request.inputProps) && typeof request.outputLocation === "string")
}



const main = async () => {
    const request: RenderRequest = JSON.parse(await readStdin())
    if (!isRenderRequest(request)) {
        throw Error("invalid prop argument")
    }

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
    const message = err instanceof Error ? err.message : String(err)
    process.stderr.write(message)
    process.exitCode = 1
})