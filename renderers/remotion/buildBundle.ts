import {resolve} from "node:path";
import {bundle} from "@remotion/bundler"


const main = async () => {
    await bundle({
                    entryPoint: resolve(__dirname, "src/index.ts"),
                    outDir: resolve(__dirname, "dist/remotion-bundle"),
                    rootDir: __dirname,
                })
}

main().catch((err) => {
    process.exitCode = 1
})