import React, { useState, useRef, useEffect } from 'react'
import { Mic, Square, RotateCcw, Check, Sparkles, AlertCircle, X, Loader2 } from 'lucide-react'
import { api } from '../api/client'
import { convertAudioToWav } from '../utils/audio'

const MAX_RECORDING_SECONDS = 29

interface VoiceIntakeRecorderProps {
  onConfirmTranscript: (transcript: string) => void
  onCancel?: () => void
  disabled?: boolean
}

type RecorderState = 'idle' | 'recording' | 'recorded' | 'transcribing' | 'review' | 'error'

export const VoiceIntakeRecorder: React.FC<VoiceIntakeRecorderProps> = ({
  onConfirmTranscript,
  onCancel,
  disabled = false,
}) => {
  const [recorderState, setRecorderState] = useState<RecorderState>('idle')
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [transcriptDraft, setTranscriptDraft] = useState<string>('')
  const [detectedLanguage, setDetectedLanguage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const mediaStreamRef = useRef<MediaStream | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const timerIntervalRef = useRef<number | null>(null)
  const startTimeRef = useRef<number>(0)

  // Safely release all microphone hardware tracks
  const stopTracks = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => {
        try {
          track.stop()
        } catch {
          // ignore already stopped tracks
        }
      })
      mediaStreamRef.current = null
    }
  }

  const stopTimer = () => {
    if (timerIntervalRef.current !== null) {
      clearInterval(timerIntervalRef.current)
      timerIntervalRef.current = null
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopTimer()
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        try {
          mediaRecorderRef.current.stop()
        } catch {
          // ignore
        }
      }
      stopTracks()
    }
  }, [])

  // Determine a supported container MIME format for the browser
  const getSupportedMimeType = (): string => {
    const candidateTypes = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg',
      'audio/mp4',
      'audio/aac',
    ]
    for (const type of candidateTypes) {
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(type)) {
        return type
      }
    }
    return '' // Fallback to browser default
  }

  const startRecording = async () => {
    setErrorMessage(null)
    setAudioBlob(null)
    setTranscriptDraft('')
    setDetectedLanguage(null)
    setElapsedSeconds(0)

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setErrorMessage('Browser microphone recording is not supported in this environment.')
      setRecorderState('error')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaStreamRef.current = stream

      const mimeType = getSupportedMimeType()
      const options = mimeType ? { mimeType } : undefined
      const recorder = new MediaRecorder(stream, options)
      mediaRecorderRef.current = recorder
      audioChunksRef.current = []

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      recorder.onstop = () => {
        const recordedBlob = new Blob(audioChunksRef.current, {
          type: mimeType || 'audio/webm',
        })
        setAudioBlob(recordedBlob)
        stopTracks()
        stopTimer()
        setRecorderState('recorded')
      }

      recorder.onerror = () => {
        stopTracks()
        stopTimer()
        setErrorMessage('An error occurred during microphone recording. Please try again.')
        setRecorderState('error')
      }

      recorder.start(250) // Collect chunks every 250ms
      setRecorderState('recording')

      // Start elapsed timer
      startTimeRef.current = Date.now()
      timerIntervalRef.current = window.setInterval(() => {
        const elapsedMs = Date.now() - startTimeRef.current
        const seconds = Math.floor(elapsedMs / 1000)
        setElapsedSeconds(seconds)
        // Leave a one-second margin below Gnani's 30-second REST limit.
        if (elapsedMs >= MAX_RECORDING_SECONDS * 1000) {
          stopRecording()
        }
      }, 250)
    } catch (err: any) {
      stopTracks()
      stopTimer()
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMessage(
          'Microphone permission was denied. Please allow microphone access in your browser settings to record your repair issue.'
        )
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setErrorMessage('No microphone device was detected on your system.')
      } else {
        setErrorMessage(err.message || 'Unable to access microphone.')
      }
      setRecorderState('error')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      try {
        mediaRecorderRef.current.stop()
      } catch {
        // ignore
      }
    }
    stopTimer()
  }

  const cancelRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      try {
        mediaRecorderRef.current.stop()
      } catch {
        // ignore
      }
    }
    stopTracks()
    stopTimer()
    setAudioBlob(null)
    setTranscriptDraft('')
    setErrorMessage(null)
    setRecorderState('idle')
    if (onCancel) onCancel()
  }

  const handleTranscribe = async () => {
    if (!audioBlob) return

    setRecorderState('transcribing')
    setErrorMessage(null)

    try {
      const wavBlob = await convertAudioToWav(audioBlob)
      const result = await api.transcribeVoice(wavBlob, 'repair_description.wav')
      setTranscriptDraft(result.transcript)
      setDetectedLanguage(result.detected_language || null)
      setRecorderState('review')
    } catch (err: any) {
      setErrorMessage(
        err.message ||
          'Failed to transcribe audio. Verify that GNANI_PRISMA_API_KEY is configured in backend/.env.'
      )
      setRecorderState('error')
    }
  }

  const handleConfirm = () => {
    if (!transcriptDraft.trim()) return
    onConfirmTranscript(transcriptDraft.trim())
    cancelRecording()
  }

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  // IDLE: Compact trigger button beside the field
  if (recorderState === 'idle') {
    return (
      <button
        type="button"
        onClick={startRecording}
        disabled={disabled}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md border border-[#E4E1E8] bg-[#F0EEFA] text-[#312E81] hover:bg-[#E4E0F5] hover:border-[#8B7BC4] focus:outline-none focus:ring-2 focus:ring-[#8B7BC4] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        title="Record repair issue with voice (Gnani Prisma STT)"
        aria-label="Record voice description"
      >
        <Mic className="w-3.5 h-3.5 text-[#D97757]" />
        <span>Record Voice</span>
      </button>
    )
  }

  return (
    <div
      className="p-3.5 rounded-lg border border-[#E4E1E8] bg-[#F7F6F3] space-y-3 transition-all"
      role="region"
      aria-live="polite"
    >
      {/* Header Info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-[#F0EEFA] flex items-center justify-center text-[#312E81]">
            <Mic className="w-4 h-4 text-[#D97757]" />
          </div>
          <div>
            <p className="text-xs font-bold text-[#27243A]">Voice Intake with Gnani Prisma STT</p>
            <p className="text-[11px] text-[#625F70]">
              Speak your repair issue. You can review and edit before confirming.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={cancelRecording}
          className="text-[#625F70] hover:text-[#27243A] p-1 rounded hover:bg-[#E4E1E8]/50 transition-colors"
          title="Close voice recorder"
          aria-label="Close voice recorder"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* STATE: Recording */}
      {recorderState === 'recording' && (
        <div className="p-3 rounded-md bg-[#FFFFFF] border border-[#E4E1E8] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#D97757] opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-[#D97757]" />
            </span>
            <span className="text-xs font-bold text-[#27243A]">Recording speech...</span>
            <span className="text-xs font-mono font-bold text-[#D97757] px-2 py-0.5 rounded bg-[#FBF4E8]">
              {formatTime(elapsedSeconds)} / 00:29
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={stopRecording}
              className="px-3 py-1.5 bg-[#D97757] hover:bg-[#B85F44] text-white text-xs font-bold rounded shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
              aria-label="Stop recording"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>Stop</span>
            </button>
            <button
              type="button"
              onClick={cancelRecording}
              className="px-2.5 py-1.5 border border-[#E4E1E8] hover:bg-[#F0EEFA] text-[#625F70] text-xs font-medium rounded transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* STATE: Recorded & Ready to Transcribe */}
      {recorderState === 'recorded' && (
        <div className="p-3 rounded-md bg-[#FFFFFF] border border-[#E4E1E8] space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-[#27243A]">
                Audio captured ({formatTime(elapsedSeconds)}).
              </span>
              <span className="text-[11px] text-[#625F70]">
                Ready to transcribe with Gnani Prisma.
              </span>
            </div>
            <button
              type="button"
              onClick={startRecording}
              className="text-xs text-[#5B4B8A] hover:underline flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Re-record</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleTranscribe}
              className="px-3.5 py-1.5 bg-[#312E81] hover:bg-[#262366] text-white text-xs font-bold rounded shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#E7B76A]" />
              <span>Transcribe Speech</span>
            </button>
            <button
              type="button"
              onClick={cancelRecording}
              className="px-2.5 py-1.5 border border-[#E4E1E8] text-[#625F70] text-xs font-medium rounded hover:bg-[#F0EEFA]"
            >
              Discard
            </button>
          </div>
        </div>
      )}

      {/* STATE: Transcribing */}
      {recorderState === 'transcribing' && (
        <div className="p-4 rounded-md bg-[#FFFFFF] border border-[#E4E1E8] flex items-center justify-center gap-3">
          <Loader2 className="w-5 h-5 text-[#312E81] animate-spin" />
          <div className="text-left">
            <p className="text-xs font-bold text-[#27243A]">
              Submitting audio to Gnani Prisma STT...
            </p>
            <p className="text-[11px] text-[#625F70]">
              Processing speech with server-side credentials
            </p>
          </div>
        </div>
      )}

      {/* STATE: Review Transcript */}
      {recorderState === 'review' && (
        <div className="p-3 rounded-md bg-[#FFFFFF] border border-[#8B7BC4] space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#312E81] bg-[#F0EEFA] px-2 py-0.5 rounded">
                Gnani Prisma Transcript
              </span>
              {detectedLanguage && (
                <span className="text-[11px] text-[#625F70]">
                  Lang: {detectedLanguage}
                </span>
              )}
            </div>
            <span className="text-[11px] text-[#625F70]">Review & edit before confirming</span>
          </div>

          <textarea
            value={transcriptDraft}
            onChange={(e) => setTranscriptDraft(e.target.value)}
            rows={3}
            className="w-full p-2 border border-[#E4E1E8] rounded text-xs text-[#27243A] focus:outline-none focus:ring-2 focus:ring-[#8B7BC4] bg-[#FFFFFF]"
            placeholder="Edit the machine transcription here if needed..."
            aria-label="Editable machine-generated transcript"
          />

          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleConfirm}
                disabled={!transcriptDraft.trim()}
                className="px-3 py-1.5 bg-[#3E7C68] hover:bg-[#346756] text-white text-xs font-bold rounded shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Confirm & Insert into Description</span>
              </button>
              <button
                type="button"
                onClick={startRecording}
                className="px-2.5 py-1.5 border border-[#E4E1E8] hover:bg-[#F0EEFA] text-[#625F70] text-xs font-medium rounded transition-colors"
              >
                Re-record
              </button>
            </div>
            <button
              type="button"
              onClick={cancelRecording}
              className="text-xs text-[#B94A48] hover:underline"
            >
              Discard
            </button>
          </div>
        </div>
      )}

      {/* STATE: Error Banner */}
      {recorderState === 'error' && (
        <div className="p-3 rounded-md bg-[#F9ECEB] border border-[#B94A48]/30 space-y-2">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-[#B94A48] shrink-0 mt-0.5" />
            <div className="text-xs text-[#B94A48] space-y-1">
              <p className="font-bold">Transcription / Recording Issue</p>
              <p className="leading-relaxed">{errorMessage}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 pt-1">
            <button
              type="button"
              onClick={startRecording}
              className="px-3 py-1 bg-[#312E81] hover:bg-[#262366] text-white text-xs font-semibold rounded transition-colors cursor-pointer"
            >
              Try Again
            </button>
            <button
              type="button"
              onClick={cancelRecording}
              className="px-2.5 py-1 border border-[#E4E1E8] text-[#625F70] text-xs font-medium rounded hover:bg-[#FFFFFF]"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
