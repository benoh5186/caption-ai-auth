export type Word = {
    id: number,
    start: number,
    end: number,
    word: string,
    text: string 
}

export type Segment = {
    id: number,
    text: string,
    start: number,
    end: number,
    words: Word[]
}

export type Transcript = {
    segments: Segment[],
    words: Word[]
}



