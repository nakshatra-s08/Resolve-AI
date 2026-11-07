const TARGET_SAMPLE_RATE = 16_000

/** Decode browser-recorded audio and encode a mono PCM WAV accepted by Gnani. */
export async function convertAudioToWav(blob: Blob): Promise<Blob> {
  const audioContext = new AudioContext()

  try {
    const decoded = await audioContext.decodeAudioData(await blob.arrayBuffer())
    const outputLength = Math.ceil(decoded.length * TARGET_SAMPLE_RATE / decoded.sampleRate)
    const monoSamples = new Float32Array(outputLength)
    const channelData = Array.from({ length: decoded.numberOfChannels }, (_, channel) =>
      decoded.getChannelData(channel)
    )
    const ratio = decoded.sampleRate / TARGET_SAMPLE_RATE

    for (let outputIndex = 0; outputIndex < outputLength; outputIndex += 1) {
      const start = Math.floor(outputIndex * ratio)
      const end = Math.min(decoded.length, Math.floor((outputIndex + 1) * ratio))
      let total = 0
      let count = 0

      for (let inputIndex = start; inputIndex < Math.max(start + 1, end); inputIndex += 1) {
        for (const channel of channelData) total += channel[inputIndex] || 0
        count += channelData.length
      }

      monoSamples[outputIndex] = count ? total / count : 0
    }

    const dataSize = monoSamples.length * 2
    const wav = new ArrayBuffer(44 + dataSize)
    const view = new DataView(wav)
    const writeText = (offset: number, value: string) => {
      for (let index = 0; index < value.length; index += 1) {
        view.setUint8(offset + index, value.charCodeAt(index))
      }
    }

    writeText(0, 'RIFF')
    view.setUint32(4, 36 + dataSize, true)
    writeText(8, 'WAVE')
    writeText(12, 'fmt ')
    view.setUint32(16, 16, true)
    view.setUint16(20, 1, true)
    view.setUint16(22, 1, true)
    view.setUint32(24, TARGET_SAMPLE_RATE, true)
    view.setUint32(28, TARGET_SAMPLE_RATE * 2, true)
    view.setUint16(32, 2, true)
    view.setUint16(34, 16, true)
    writeText(36, 'data')
    view.setUint32(40, dataSize, true)

    for (let index = 0; index < monoSamples.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, monoSamples[index]))
      view.setInt16(44 + index * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
    }

    return new Blob([wav], { type: 'audio/wav' })
  } finally {
    await audioContext.close()
  }
}
