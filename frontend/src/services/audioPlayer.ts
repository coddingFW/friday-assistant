// Reproduz o áudio da resposta (TTS) roteando por um AnalyserNode da Web Audio
// API, para o avatar fazer lip-sync pela amplitude do som em tempo real.
// Fonte única de reprodução: autoplay e botão "Ouvir" passam por aqui.

class AudioPlayer {
  private ctx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private data: Uint8Array<ArrayBuffer> | null = null;
  private current: HTMLAudioElement | null = null;
  private playing = false;

  private ensure(): void {
    if (this.ctx) return;
    this.ctx = new AudioContext();
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 256;
    this.data = new Uint8Array(new ArrayBuffer(this.analyser.frequencyBinCount));
    this.analyser.connect(this.ctx.destination);
  }

  /**
   * Destrava o áudio dentro de um gesto do usuário (clique/Enter). A fala chega
   * segundos depois da resposta; sem isto, o AudioContext ficaria suspenso e a
   * primeira fala não tocaria (política de autoplay dos navegadores).
   */
  async unlock(): Promise<void> {
    this.ensure();
    if (this.ctx!.state === "suspended") {
      await this.ctx!.resume().catch(() => undefined);
    }
  }

  async play(url: string): Promise<void> {
    this.ensure();
    if (this.ctx!.state === "suspended") {
      await this.ctx!.resume().catch(() => undefined);
    }
    this.stop();

    const audio = new Audio(url);
    const source = this.ctx!.createMediaElementSource(audio);
    source.connect(this.analyser!);
    audio.onended = () => {
      this.playing = false;
    };
    this.current = audio;
    this.playing = true;
    try {
      await audio.play();
    } catch {
      this.playing = false; // autoplay bloqueado; botão "Ouvir" tenta de novo
    }
  }

  stop(): void {
    if (this.current) {
      this.current.pause();
      this.current = null;
    }
    this.playing = false;
  }

  get speaking(): boolean {
    return this.playing;
  }

  /** Amplitude atual da fala (0..1), via RMS do sinal no domínio do tempo. */
  amplitude(): number {
    if (!this.analyser || !this.data || !this.playing) return 0;
    this.analyser.getByteTimeDomainData(this.data);
    let sum = 0;
    for (let i = 0; i < this.data.length; i++) {
      const v = (this.data[i] - 128) / 128;
      sum += v * v;
    }
    const rms = Math.sqrt(sum / this.data.length);
    return Math.min(1, rms * 3.2); // ganho para uma faixa de boca agradável
  }
}

export const audioPlayer = new AudioPlayer();
