/**
 * Clawd Bot (智能機械蟹) — Zero-Dependency Procedural Animation Rig
 * Supports both real-time browser interaction and deterministic frame-by-frame video rendering.
 */
export class ClawdBotRig {
  /**
   * @param {SVGElement} svgRoot - The root <svg> element containing Clawd Bot layers
   */
  constructor(svgRoot) {
    this.root = svgRoot;
    this.state = 'idle'; // 'idle' | 'thinking' | 'happy' | 'sleep'
    this.targetLook = { x: 0, y: 0 };
    this.smoothLook = { x: 0, y: 0 };
    this.pokeAmount = 0;

    this.els = {
      shadow: svgRoot.querySelector('#shadow'),
      actor: svgRoot.querySelector('#actor'),
      spark: svgRoot.querySelector('#crab-spark'),
      clawL: svgRoot.querySelector('#claw-l'),
      clawR: svgRoot.querySelector('#claw-r'),
      face: svgRoot.querySelector('#face'),
      eyesNormal: svgRoot.querySelector('#eyes-normal'),
      eyesHappy: svgRoot.querySelector('#eyes-happy'),
      eyesSleep: svgRoot.querySelector('#eyes-sleep'),
      mouth: svgRoot.querySelector('#mouth'),
      fx: svgRoot.querySelector('#fx'),
    };
  }

  /**
   * Switch animation state: 'idle' | 'thinking' | 'happy' | 'sleep'
   */
  setState(newState) {
    this.state = newState;
    const { eyesNormal, eyesHappy, eyesSleep, mouth, fx } = this.els;

    eyesNormal.style.display = (newState === 'idle' || newState === 'thinking') ? 'block' : 'none';
    eyesHappy.style.display = (newState === 'happy') ? 'block' : 'none';
    eyesSleep.style.display = (newState === 'sleep') ? 'block' : 'none';

    if (newState === 'sleep') {
      mouth.setAttribute('stroke', '#FF8577');
      mouth.setAttribute('d', 'M-5,9 Q0,5 5,9');
    } else if (newState === 'thinking') {
      mouth.setAttribute('stroke', '#F6B966');
      mouth.setAttribute('d', 'M-6,8 L6,8');
    } else {
      mouth.setAttribute('stroke', '#68E399');
      mouth.setAttribute('d', 'M-5,7 Q0,11 5,7');
    }

    if (fx) {
      if (newState === 'happy') {
        fx.innerHTML = `
          <g class="burst">
            <text x="-70" y="-54" font-size="20">✨</text>
            <text x="54" y="-56" font-size="18" fill="#D97757">✻</text>
            <text x="0" y="-82" font-size="18" text-anchor="middle" fill="#FF7E79">♥</text>
          </g>`;
      } else if (newState === 'sleep') {
        fx.innerHTML = `
          <text x="48" y="-55" font-size="18" font-weight="bold" fill="#8C857B">Z</text>
          <text x="64" y="-72" font-size="14" font-weight="bold" fill="#A8A096">z</text>
          <text x="76" y="-85" font-size="11" font-weight="bold" fill="#C2B9AE">z</text>`;
      } else if (newState === 'thinking') {
        fx.innerHTML = `
          <g transform="translate(56, -68)">
            <circle cx="0" cy="0" r="16" fill="#FFF" stroke="#252422" stroke-width="2.5"/>
            <text x="0" y="6" font-size="16" text-anchor="middle" fill="#D97757">✻</text>
          </g>`;
      } else {
        fx.innerHTML = '';
      }
    }
  }

  /**
   * Set normalized gaze target in [-1, 1]
   */
  setLookAt(nx, ny) {
    this.targetLook.x = Math.max(-1, Math.min(1, nx));
    this.targetLook.y = Math.max(-1, Math.min(1, ny));
  }

  /**
   * Trigger bouncy squash-and-stretch poke reaction
   */
  poke() {
    this.pokeAmount = 1.0;
  }

  /**
   * Deterministic frame update at time `t` (in seconds)
   */
  tick(t) {
    this.smoothLook.x += (this.targetLook.x - this.smoothLook.x) * 0.12;
    this.smoothLook.y += (this.targetLook.y - this.smoothLook.y) * 0.12;

    if (this.pokeAmount > 0.01) this.pokeAmount *= 0.88;
    else this.pokeAmount = 0;

    const speedMult =
      this.state === 'thinking' ? 2.2 :
      this.state === 'happy' ? 2.8 :
      this.state === 'sleep' ? 0.5 : 1.0;

    const phase = t * 2.5 * speedMult;
    let bobY = Math.sin(phase) * 4.5;
    if (this.state === 'happy') {
      bobY = -Math.abs(Math.sin(t * 7)) * 15;
    } else if (this.state === 'sleep') {
      bobY = 5 + Math.sin(t * 1.4) * 1.8;
    }

    const breatheSquish = Math.sin(phase) * 0.03;
    const scaleX = 1 + breatheSquish + Math.sin(this.pokeAmount * Math.PI * 3) * this.pokeAmount * 0.25;
    const scaleY = 1 - breatheSquish - Math.sin(this.pokeAmount * Math.PI * 3) * this.pokeAmount * 0.22;

    this.els.actor.setAttribute(
      'transform',
      `translate(0, ${bobY.toFixed(2)}) scale(${scaleX.toFixed(3)}, ${scaleY.toFixed(3)})`
    );
    this.els.shadow.setAttribute('rx', (50 - bobY * 0.35).toFixed(1));

    const lookX = this.state === 'sleep' ? 0 : this.smoothLook.x * 7;
    const lookY = this.state === 'sleep' ? 1.5 : this.smoothLook.y * 4.5;
    this.els.face.setAttribute('transform', `translate(${lookX.toFixed(2)}, ${lookY.toFixed(2)})`);

    // Antenna spark spin
    this.els.spark.setAttribute('transform', `translate(0, -6) rotate(${(t * 90 * speedMult).toFixed(1)})`);

    // Symmetrical Floating C-Claws
    if (this.state === 'thinking') {
      const clY = Math.sin(t * 24) * 6;
      const crY = Math.cos(t * 24) * 6;
      this.els.clawL.setAttribute('transform', `translate(-58, ${(2 + clY).toFixed(2)}) rotate(15)`);
      this.els.clawR.setAttribute('transform', `translate(58, ${(2 + crY).toFixed(2)}) rotate(-15)`);
    } else if (this.state === 'happy') {
      const cheer = Math.sin(t * 14) * 18;
      this.els.clawL.setAttribute('transform', `translate(-64, -10) rotate(${(25 + cheer).toFixed(1)})`);
      this.els.clawR.setAttribute('transform', `translate(64, -10) rotate(${(-25 - cheer).toFixed(1)})`);
    } else if (this.state === 'sleep') {
      this.els.clawL.setAttribute('transform', 'translate(-54, 10) rotate(-12)');
      this.els.clawR.setAttribute('transform', 'translate(54, 10) rotate(12)');
    } else {
      const hover = Math.sin(t * 3) * 4;
      const tilt = Math.sin(t * 2) * 6;
      this.els.clawL.setAttribute('transform', `translate(-66, ${(2 + hover).toFixed(2)}) rotate(${tilt.toFixed(1)})`);
      this.els.clawR.setAttribute('transform', `translate(66, ${(2 + hover).toFixed(2)}) rotate(${(-tilt).toFixed(1)})`);
    }
  }
}
