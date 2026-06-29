/** Simulated qualification call for demo / interview mode. */

export const DEMO_SCRIPT = [
  {
    delay: 1200,
    role: 'assistant',
    text: 'Hi there! This is Alex from Karta SDR. Thanks for your interest in our AI voice platform. May I ask who I\'m speaking with?',
    state: 'INTRO',
  },
  {
    delay: 3500,
    role: 'user',
    text: 'Hi, my name is Sarah Johnson.',
    process: true,
  },
  {
    delay: 2800,
    role: 'assistant',
    text: 'Great to meet you, Sarah! This will be a quick five-minute qualification call. Is now a good time?',
    state: 'PERMISSION',
  },
  {
    delay: 2500,
    role: 'user',
    text: 'Yes, now is a good time.',
    process: true,
  },
  {
    delay: 3200,
    role: 'assistant',
    text: 'Can you tell me your company name, industry, and approximate number of employees?',
    state: 'COMPANY_INFO',
  },
  {
    delay: 4000,
    role: 'user',
    text: 'We are TechFlow Inc, a SaaS company with about 75 employees.',
    process: true,
  },
  {
    delay: 3000,
    role: 'assistant',
    text: 'Got it. What are your approximate monthly inbound and outbound call volumes?',
    state: 'CALL_VOLUME',
  },
  {
    delay: 3800,
    role: 'user',
    text: 'About 5000 inbound and 2000 outbound calls per month.',
    process: true,
  },
  {
    delay: 2800,
    role: 'assistant',
    text: 'What are you currently using for sales calls or lead qualification?',
    state: 'CURRENT_PROCESS',
  },
  {
    delay: 3200,
    role: 'user',
    text: 'We use a manual SDR team right now.',
    process: true,
  },
  {
    delay: 2800,
    role: 'assistant',
    text: 'What are the biggest challenges with your current approach?',
    state: 'PAIN_POINTS',
  },
  {
    delay: 3500,
    role: 'user',
    text: 'Our biggest challenges are high cost and inconsistent qualification.',
    process: true,
  },
  {
    delay: 3000,
    role: 'assistant',
    text: 'What monthly budget range are you considering for an AI voice solution?',
    state: 'BUDGET',
  },
  {
    delay: 3200,
    role: 'user',
    text: 'Our budget is between 2000 and 10000 per month.',
    process: true,
  },
  {
    delay: 2800,
    role: 'assistant',
    text: 'When are you looking to implement — immediately, within three months, or longer?',
    state: 'TIMELINE',
  },
  {
    delay: 3000,
    role: 'user',
    text: 'We want to implement within 3 months.',
    process: true,
  },
  {
    delay: 3200,
    role: 'assistant',
    text: 'Thank you for sharing all of that. Based on what you\'ve told me, I think Karta SDR could be a strong fit.',
    state: 'LEAD_SCORING',
  },
  {
    delay: 3500,
    role: 'assistant',
    text: 'I\'d love to set up a demo with our sales team. What day works best, and what\'s the best email?',
    state: 'BOOKING',
  },
  {
    delay: 4000,
    role: 'user',
    text: 'Yes, schedule a demo for Tuesday at 2pm. My email is sarah@techflow.io.',
    process: true,
  },
  {
    delay: 2000,
    role: 'assistant',
    text: 'Perfect! I\'ve noted Tuesday at 2pm. Our team will send a calendar invite to sarah@techflow.io. Thank you for your time!',
    state: 'END_CALL',
  },
]

export function runDemoCall({ callId, onStep, onSpeakingChange, sendTranscript, sendEvent, onComplete }) {
  let cancelled = false
  let timeoutId

  const run = async (index) => {
    if (cancelled || index >= DEMO_SCRIPT.length) {
      onSpeakingChange(null)
      onComplete?.()
      return
    }

    const step = DEMO_SCRIPT[index]
    await new Promise((r) => { timeoutId = setTimeout(r, step.delay) })
    if (cancelled) return

    onSpeakingChange(step.role)

    if (step.role === 'assistant') {
      onStep({ role: 'assistant', text: step.text, state: step.state })
      await sendEvent?.('speech-start', { role: 'assistant' })
      await new Promise((r) => setTimeout(r, 800))
      await sendEvent?.('speech-end', {})
      onSpeakingChange(null)
      run(index + 1)
    } else {
      onStep({ role: 'user', text: step.text })
      await sendEvent?.('speech-start', { role: 'user' })
      if (step.process && sendTranscript) {
        await sendTranscript(callId, 'user', step.text)
      }
      await sendEvent?.('speech-end', {})
      onSpeakingChange(null)
      run(index + 1)
    }
  }

  sendEvent?.('call-start', {})
  run(0)

  return () => {
    cancelled = true
    clearTimeout(timeoutId)
    sendEvent?.('call-end', {})
  }
}
