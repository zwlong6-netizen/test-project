// 活力贪吃蛇核心逻辑 (Vibrant Snake Engine)

const GRID_SIZE = 24; // 24 x 24 网格
const LOGICAL_SIZE = 600; // 画布逻辑尺寸
const CELL_SIZE = LOGICAL_SIZE / GRID_SIZE; // 每格 25px

const SPEED_CONFIGS = {
  slow: 125,
  normal: 90,
  fast: 65,
  insane: 45
};

class VibrantSnakeGame {
  constructor() {
    this.canvas = document.getElementById('game-canvas');
    this.ctx = this.canvas.getContext('2d');

    // UI 元素绑定
    this.scoreEl = document.getElementById('current-score');
    this.highScoreEl = document.getElementById('high-score');
    this.comboEl = document.getElementById('combo-multiplier');
    this.lengthEl = document.getElementById('snake-length');
    this.comboPopup = document.getElementById('combo-popup');

    this.overlay = document.getElementById('overlay');
    this.overlayTitle = document.getElementById('overlay-title');
    this.overlayDesc = document.getElementById('overlay-desc');
    this.overlayStats = document.getElementById('overlay-stats');
    this.finalScoreEl = document.getElementById('final-score');
    this.finalHighScoreEl = document.getElementById('final-high-score');
    this.finalApplesEl = document.getElementById('final-apples');
    this.finalComboEl = document.getElementById('final-combo');
    this.btnStart = document.getElementById('btn-start');

    this.btnTheme = document.getElementById('btn-theme');
    this.themeIcon = document.getElementById('theme-icon');
    this.btnSound = document.getElementById('btn-sound');
    this.soundIcon = document.getElementById('sound-icon');
    this.btnHelp = document.getElementById('btn-help');
    this.helpModal = document.getElementById('help-modal');
    this.btnCloseHelp = document.getElementById('btn-close-help');
    this.btnModalOk = document.getElementById('btn-modal-ok');

    // 设置与模式
    this.mode = 'classic'; // 'classic' 或 'wrap'
    this.speedLevel = 'normal'; // 'slow', 'normal', 'fast', 'insane'
    this.gameState = 'READY'; // 'READY', 'PLAYING', 'PAUSED', 'GAMEOVER'

    // 高分持久化
    this.highScore = parseInt(localStorage.getItem('neon_snake_highscore') || '0', 10);
    this.highScoreEl.textContent = this.highScore;

    // 主题初始化（默认亮色明亮主题）
    this.initTheme();

    // 适配高清屏幕 (Retina Display)
    this.setupHiDPI();

    // 游戏核心状态
    this.snake = [];
    this.dir = { x: 1, y: 0 };
    this.inputQueue = [];
    this.food = null;
    this.specialFood = null; // { x, y, type: 'golden'|'freeze', timer, maxTimer }
    this.particles = [];
    this.score = 0;
    this.applesCount = 0;
    this.combo = 0;
    this.maxCombo = 1.0;
    this.comboTimer = 0; // 连击有效倒计时
    this.freezeEffectTimer = 0; // 冰晶减速特效时间

    // 循环驱动参数
    this.lastTickTime = 0;
    this.accumulatedTime = 0;
    this.screenShake = 0;

    this.initSoundUI();
    this.bindEvents();
    this.resetGame();
    this.render(); // 渲染初始画面

    // 启动主渲染循环 (60/120fps)
    requestAnimationFrame((t) => this.gameLoop(t));
  }

  initTheme() {
    // 优先读取本地设置，默认为 light（明亮清爽）
    const savedTheme = localStorage.getItem('neon_snake_theme') || 'light';
    if (savedTheme === 'dark') {
      document.body.classList.add('theme-dark');
      this.themeIcon.textContent = '🌙';
    } else {
      document.body.classList.remove('theme-dark');
      this.themeIcon.textContent = '☀️';
    }
  }

  toggleTheme() {
    const isDark = document.body.classList.toggle('theme-dark');
    this.themeIcon.textContent = isDark ? '🌙' : '☀️';
    localStorage.setItem('neon_snake_theme', isDark ? 'dark' : 'light');
    window.soundCtrl.playClick();
  }

  setupHiDPI() {
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = LOGICAL_SIZE * dpr;
    this.canvas.height = LOGICAL_SIZE * dpr;
    this.ctx.scale(dpr, dpr);
  }

  initSoundUI() {
    const isMuted = window.soundCtrl.isMuted;
    this.soundIcon.textContent = isMuted ? '🔇' : '🔊';
  }

  resetGame() {
    // 居中放置初始长度为 3 的蛇
    const midY = Math.floor(GRID_SIZE / 2);
    this.snake = [
      { x: 6, y: midY },
      { x: 5, y: midY },
      { x: 4, y: midY }
    ];
    this.dir = { x: 1, y: 0 };
    this.inputQueue = [];
    this.score = 0;
    this.applesCount = 0;
    this.combo = 0;
    this.maxCombo = 1.0;
    this.comboTimer = 0;
    this.freezeEffectTimer = 0;
    this.particles = [];
    this.specialFood = null;

    this.spawnFood();

    this.updateStatsUI();
  }

  startGame() {
    window.soundCtrl.ensureContext();
    window.soundCtrl.playClick();
    this.resetGame();
    this.gameState = 'PLAYING';
    this.overlay.classList.add('hidden');
  }

  pauseGame() {
    if (this.gameState === 'PLAYING') {
      this.gameState = 'PAUSED';
      this.overlayTitle.textContent = '游戏暂停';
      this.overlayDesc.textContent = '按空格键或点击下方按钮继续游戏';
      this.overlayStats.classList.add('hidden');
      this.btnStart.textContent = '继续游戏 (Space)';
      this.overlay.classList.remove('hidden');
      window.soundCtrl.playClick();
    } else if (this.gameState === 'PAUSED') {
      this.resumeGame();
    }
  }

  resumeGame() {
    if (this.gameState === 'PAUSED') {
      this.gameState = 'PLAYING';
      this.overlay.classList.add('hidden');
      window.soundCtrl.playClick();
    }
  }

  gameOver() {
    this.gameState = 'GAMEOVER';
    window.soundCtrl.playDie();
    this.screenShake = 16;

    // 蛇身破碎粒子爆发
    this.snake.forEach((seg) => {
      this.createExplosion(
        seg.x * CELL_SIZE + CELL_SIZE / 2,
        seg.y * CELL_SIZE + CELL_SIZE / 2,
        '#0284c7',
        6
      );
    });

    if (this.score > this.highScore) {
      this.highScore = this.score;
      localStorage.setItem('neon_snake_highscore', this.highScore.toString());
      this.highScoreEl.textContent = this.highScore;
    }

    // 更新结算面板
    this.finalScoreEl.textContent = this.score;
    this.finalHighScoreEl.textContent = this.highScore;
    this.finalApplesEl.textContent = this.applesCount;
    this.finalComboEl.textContent = `x${this.maxCombo.toFixed(1)}`;

    this.overlayTitle.textContent = '游戏结束';
    this.overlayDesc.textContent = this.score === this.highScore && this.score > 0
      ? '🎉 太棒了！刷新了历史最高纪录！'
      : '不小心撞车了，整装再战吧！';
    this.overlayStats.classList.remove('hidden');
    this.btnStart.textContent = '再来一局 (Space)';
    this.overlay.classList.remove('hidden');
  }

  // 随机空位置刷食物
  getEmptyCell() {
    const occupied = new Set();
    this.snake.forEach(seg => occupied.add(`${seg.x},${seg.y}`));
    if (this.food) occupied.add(`${this.food.x},${this.food.y}`);
    if (this.specialFood) occupied.add(`${this.specialFood.x},${this.specialFood.y}`);

    const empties = [];
    for (let x = 0; x < GRID_SIZE; x++) {
      for (let y = 0; y < GRID_SIZE; y++) {
        if (!occupied.has(`${x},${y}`)) {
          empties.push({ x, y });
        }
      }
    }

    if (empties.length === 0) return null;
    const idx = Math.floor(Math.random() * empties.length);
    return empties[idx];
  }

  spawnFood() {
    const pos = this.getEmptyCell();
    if (!pos) return;
    this.food = { x: pos.x, y: pos.y, type: 'apple' };

    // 28% 几率伴随刷出特殊食物（金苹果或冰晶）
    if (!this.specialFood && Math.random() < 0.28 && this.snake.length > 4) {
      const specPos = this.getEmptyCell();
      if (specPos) {
        const type = Math.random() < 0.6 ? 'golden' : 'freeze';
        this.specialFood = {
          x: specPos.x,
          y: specPos.y,
          type: type,
          timer: 160,
          maxTimer: 160
        };
      }
    }
  }

  createExplosion(x, y, color, count = 12) {
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 1.5 + Math.random() * 4.5;
      this.particles.push({
        x: x,
        y: y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        color: color,
        alpha: 1.0,
        size: 2.5 + Math.random() * 3.5,
        life: 0,
        maxLife: 20 + Math.random() * 20
      });
    }
  }

  handleDirectionInput(newDir) {
    // 防止快速按键自撞：从输入队列或当前方向比较
    const lastDir = this.inputQueue.length > 0
      ? this.inputQueue[this.inputQueue.length - 1]
      : this.dir;

    // 不能掉头
    if (newDir.x + lastDir.x === 0 && newDir.y + lastDir.y === 0) {
      return;
    }

    // 限制队列最大缓存 2 个按键指令
    if (this.inputQueue.length < 2) {
      this.inputQueue.push(newDir);
    }
  }

  updateStatsUI() {
    this.scoreEl.textContent = this.score;
    this.lengthEl.textContent = this.snake.length;
    const mult = 1.0 + Math.min(this.combo * 0.2, 2.0);
    this.comboEl.textContent = `x${mult.toFixed(1)}`;
  }

  triggerComboPopup(multiplier) {
    this.comboPopup.textContent = `COMBO x${multiplier.toFixed(1)}!`;
    this.comboPopup.classList.remove('hidden');
    this.comboPopup.classList.add('show');
    clearTimeout(this.comboPopupTimer);
    this.comboPopupTimer = setTimeout(() => {
      this.comboPopup.classList.remove('show');
      setTimeout(() => this.comboPopup.classList.add('hidden'), 200);
    }, 700);
  }

  // 贪吃蛇逻辑更新帧
  tick() {
    if (this.gameState !== 'PLAYING') return;

    // 从指令队列取下一个方向
    if (this.inputQueue.length > 0) {
      this.dir = this.inputQueue.shift();
    }

    // 计算蛇头下一步位置
    const head = this.snake[0];
    let nextX = head.x + this.dir.x;
    let nextY = head.y + this.dir.y;

    // 边界检测
    if (this.mode === 'wrap') {
      if (nextX < 0) nextX = GRID_SIZE - 1;
      else if (nextX >= GRID_SIZE) nextX = 0;
      if (nextY < 0) nextY = GRID_SIZE - 1;
      else if (nextY >= GRID_SIZE) nextY = 0;
    } else {
      // 经典撞墙死
      if (nextX < 0 || nextX >= GRID_SIZE || nextY < 0 || nextY >= GRID_SIZE) {
        this.gameOver();
        return;
      }
    }

    // 自撞身体检测
    for (let i = 0; i < this.snake.length - 1; i++) {
      if (this.snake[i].x === nextX && this.snake[i].y === nextY) {
        this.gameOver();
        return;
      }
    }

    const newHead = { x: nextX, y: nextY };
    this.snake.unshift(newHead);

    let ateFood = false;

    // 检查是否吃到普通苹果
    if (this.food && nextX === this.food.x && nextY === this.food.y) {
      ateFood = true;
      this.applesCount++;
      this.combo++;
      this.comboTimer = 35; // 连击窗口时间

      const multiplier = 1.0 + Math.min(this.combo * 0.2, 2.0);
      if (multiplier > this.maxCombo) this.maxCombo = multiplier;

      const gainedScore = Math.round(10 * multiplier);
      this.score += gainedScore;

      if (this.combo >= 2) {
        this.triggerComboPopup(multiplier);
        window.soundCtrl.playCombo();
      } else {
        window.soundCtrl.playEat();
      }

      this.createExplosion(
        nextX * CELL_SIZE + CELL_SIZE / 2,
        nextY * CELL_SIZE + CELL_SIZE / 2,
        '#f43f5e',
        14
      );

      this.spawnFood();
    }

    // 检查是否吃到特殊果实
    if (this.specialFood && nextX === this.specialFood.x && nextY === this.specialFood.y) {
      ateFood = true;
      const type = this.specialFood.type;
      const multiplier = 1.0 + Math.min(this.combo * 0.2, 2.0);

      if (type === 'golden') {
        const bonus = Math.round(50 * multiplier);
        this.score += bonus;
        this.createExplosion(
          nextX * CELL_SIZE + CELL_SIZE / 2,
          nextY * CELL_SIZE + CELL_SIZE / 2,
          '#f59e0b',
          22
        );
      } else if (type === 'freeze') {
        this.score += Math.round(20 * multiplier);
        this.freezeEffectTimer = 90; // 减速持续时间
        this.createExplosion(
          nextX * CELL_SIZE + CELL_SIZE / 2,
          nextY * CELL_SIZE + CELL_SIZE / 2,
          '#0284c7',
          18
        );
      }

      window.soundCtrl.playSpecial();
      this.specialFood = null;
    }

    // 如果没吃到食物，移除蛇尾保持长度不变
    if (!ateFood) {
      this.snake.pop();
    }

    // 特殊食物倒计时处理
    if (this.specialFood) {
      this.specialFood.timer--;
      if (this.specialFood.timer <= 0) {
        this.specialFood = null;
      }
    }

    // 连击计时器衰减
    if (this.comboTimer > 0) {
      this.comboTimer--;
      if (this.comboTimer === 0) {
        this.combo = 0;
      }
    }

    // 冰晶特效计时器衰减
    if (this.freezeEffectTimer > 0) {
      this.freezeEffectTimer--;
    }

    this.updateStatsUI();
  }

  // 主循环
  gameLoop(currentTime) {
    if (!this.lastTickTime) this.lastTickTime = currentTime;
    const delta = currentTime - this.lastTickTime;
    this.lastTickTime = currentTime;

    // 计算当前移动速度步长
    let interval = SPEED_CONFIGS[this.speedLevel];
    if (this.freezeEffectTimer > 0) {
      interval = Math.round(interval * 1.35); // 冰冻减速
    }

    this.accumulatedTime += delta;
    while (this.accumulatedTime >= interval) {
      this.tick();
      this.accumulatedTime -= interval;
    }

    // 更新粒子效果
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.vx *= 0.94;
      p.vy *= 0.94;
      p.life++;
      p.alpha = 1.0 - (p.life / p.maxLife);
      if (p.life >= p.maxLife) {
        this.particles.splice(i, 1);
      }
    }

    // 屏幕震动衰减
    if (this.screenShake > 0) {
      this.screenShake *= 0.85;
      if (this.screenShake < 0.5) this.screenShake = 0;
    }

    this.render();

    requestAnimationFrame((t) => this.gameLoop(t));
  }

  // 渲染绘制
  render() {
    const ctx = this.ctx;
    const isDark = document.body.classList.contains('theme-dark');

    ctx.save();

    // 屏幕震动位移
    if (this.screenShake > 0) {
      const shakeX = (Math.random() - 0.5) * this.screenShake;
      const shakeY = (Math.random() - 0.5) * this.screenShake;
      ctx.translate(shakeX, shakeY);
    }

    // 清屏：明亮模式下为纯白/清爽微灰，暗色模式下为深邃深蓝
    ctx.fillStyle = isDark ? '#060911' : '#ffffff';
    ctx.fillRect(0, 0, LOGICAL_SIZE, LOGICAL_SIZE);

    // 绘制网格线与交叉点
    this.renderGrid(ctx, isDark);

    // 绘制穿墙模式边缘提示边框
    if (this.mode === 'wrap') {
      ctx.strokeStyle = isDark ? 'rgba(0, 240, 255, 0.35)' : 'rgba(2, 132, 199, 0.4)';
      ctx.lineWidth = 2.5;
      ctx.setLineDash([8, 8]);
      ctx.strokeRect(1, 1, LOGICAL_SIZE - 2, LOGICAL_SIZE - 2);
      ctx.setLineDash([]);
    }

    // 绘制粒子
    this.renderParticles(ctx);

    // 绘制特殊食物
    if (this.specialFood) {
      this.renderSpecialFood(ctx, isDark);
    }

    // 绘制普通苹果
    if (this.food) {
      this.renderFood(ctx, isDark);
    }

    // 绘制蛇
    this.renderSnake(ctx, isDark);

    ctx.restore();
  }

  renderGrid(ctx, isDark) {
    ctx.strokeStyle = isDark ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.045)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= GRID_SIZE; i++) {
      const pos = i * CELL_SIZE;
      ctx.beginPath();
      ctx.moveTo(pos, 0);
      ctx.lineTo(pos, LOGICAL_SIZE);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(0, pos);
      ctx.lineTo(LOGICAL_SIZE, pos);
      ctx.stroke();
    }
  }

  renderFood(ctx, isDark) {
    const x = this.food.x * CELL_SIZE + CELL_SIZE / 2;
    const y = this.food.y * CELL_SIZE + CELL_SIZE / 2;
    const radius = CELL_SIZE * 0.38;

    // 呼吸动态发光半径
    const pulse = Math.sin(Date.now() / 180) * 1.8;

    ctx.save();
    if (isDark) {
      ctx.shadowColor = '#f43f5e';
      ctx.shadowBlur = 14 + pulse;
    } else {
      ctx.shadowColor = 'rgba(244, 63, 94, 0.4)';
      ctx.shadowBlur = 8;
    }

    // 苹果外球
    ctx.fillStyle = '#f43f5e';
    ctx.beginPath();
    ctx.arc(x, y + 1, radius + pulse * 0.3, 0, Math.PI * 2);
    ctx.fill();

    // 苹果高光点
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#fda4af';
    ctx.beginPath();
    ctx.arc(x - radius * 0.3, y - radius * 0.3, radius * 0.35, 0, Math.PI * 2);
    ctx.fill();

    // 苹果叶子
    ctx.fillStyle = '#10b981';
    ctx.beginPath();
    ctx.ellipse(x + 2, y - radius * 0.9, 3, 5, Math.PI / 4, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  renderSpecialFood(ctx, isDark) {
    const item = this.specialFood;
    const x = item.x * CELL_SIZE + CELL_SIZE / 2;
    const y = item.y * CELL_SIZE + CELL_SIZE / 2;
    const radius = CELL_SIZE * 0.42;

    ctx.save();

    // 倒计时环
    const progress = item.timer / item.maxTimer;
    ctx.strokeStyle = item.type === 'golden' ? '#f59e0b' : '#0284c7';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(x, y, radius + 4, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * progress);
    ctx.stroke();

    // 发光主体
    ctx.shadowColor = item.type === 'golden' ? '#f59e0b' : '#0284c7';
    ctx.shadowBlur = isDark ? 16 : 8;
    ctx.fillStyle = item.type === 'golden' ? '#fbbf24' : '#38bdf8';

    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();

    // 内部图标
    ctx.shadowBlur = 0;
    ctx.font = `${Math.floor(CELL_SIZE * 0.6)}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(item.type === 'golden' ? '⭐' : '❄️', x, y + 1);

    ctx.restore();
  }

  renderSnake(ctx, isDark) {
    if (this.snake.length === 0) return;

    for (let i = this.snake.length - 1; i >= 0; i--) {
      const seg = this.snake[i];
      const isHead = i === 0;
      const x = seg.x * CELL_SIZE;
      const y = seg.y * CELL_SIZE;
      const pad = 1.5;

      ctx.save();

      if (isHead) {
        // 头部
        const headColor = isDark ? '#00f0ff' : '#0284c7';
        ctx.shadowColor = headColor;
        ctx.shadowBlur = isDark ? 16 : 6;
        ctx.fillStyle = headColor;

        // 圆角矩形蛇头
        this.roundRect(ctx, x + pad, y + pad, CELL_SIZE - pad * 2, CELL_SIZE - pad * 2, 8);
        ctx.fill();

        // 绘制生动的眼睛
        ctx.shadowBlur = 0;
        this.renderSnakeEyes(ctx, seg, isDark);
      } else {
        // 身体渐变色
        const ratio = i / this.snake.length;
        const color = isDark
          ? this.getSnakeSegmentColorDark(ratio)
          : this.getSnakeSegmentColorLight(ratio);

        ctx.shadowColor = color;
        ctx.shadowBlur = isDark ? 6 : 2;
        ctx.fillStyle = color;

        this.roundRect(ctx, x + pad, y + pad, CELL_SIZE - pad * 2, CELL_SIZE - pad * 2, 6);
        ctx.fill();
      }

      ctx.restore();
    }
  }

  getSnakeSegmentColorLight(ratio) {
    // 明亮模式：从清澈碧绿(#10b981) 过渡到海蓝(#0284c7) 再到紫罗兰(#7c3aed)
    const r = Math.round(16 + ratio * (124 - 16));
    const g = Math.round(185 + ratio * (58 - 185));
    const b = Math.round(129 + ratio * (237 - 129));
    return `rgb(${r}, ${g}, ${b})`;
  }

  getSnakeSegmentColorDark(ratio) {
    // 暗黑模式：从青绿(#10b981) 过渡到霓虹紫(#8b5cf6)
    const r = Math.round(16 + ratio * (139 - 16));
    const g = Math.round(185 + ratio * (92 - 185));
    const b = Math.round(129 + ratio * (246 - 129));
    return `rgb(${r}, ${g}, ${b})`;
  }

  renderSnakeEyes(ctx, head, isDark) {
    const cx = head.x * CELL_SIZE + CELL_SIZE / 2;
    const cy = head.y * CELL_SIZE + CELL_SIZE / 2;
    const eyeOffset = CELL_SIZE * 0.22;
    const eyeRadius = CELL_SIZE * 0.17;
    const pupilRadius = CELL_SIZE * 0.085;

    let eye1X, eye1Y, eye2X, eye2Y;
    let pupilOffsetX = this.dir.x * 1.5;
    let pupilOffsetY = this.dir.y * 1.5;

    if (this.dir.x !== 0) {
      eye1X = cx + this.dir.x * eyeOffset * 0.8;
      eye1Y = cy - eyeOffset;
      eye2X = cx + this.dir.x * eyeOffset * 0.8;
      eye2Y = cy + eyeOffset;
    } else {
      eye1X = cx - eyeOffset;
      eye1Y = cy + this.dir.y * eyeOffset * 0.8;
      eye2X = cx + eyeOffset;
      eye2Y = cy + this.dir.y * eyeOffset * 0.8;
    }

    // 眼白（明亮模式下带有一圈精致描边）
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(eye1X, eye1Y, eyeRadius, 0, Math.PI * 2);
    ctx.arc(eye2X, eye2Y, eyeRadius, 0, Math.PI * 2);
    ctx.fill();

    if (!isDark) {
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.15)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // 瞳孔（朝向行进方向）
    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.arc(eye1X + pupilOffsetX, eye1Y + pupilOffsetY, pupilRadius, 0, Math.PI * 2);
    ctx.arc(eye2X + pupilOffsetX, eye2Y + pupilOffsetY, pupilRadius, 0, Math.PI * 2);
    ctx.fill();
  }

  renderParticles(ctx) {
    this.particles.forEach(p => {
      ctx.save();
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });
  }

  roundRect(ctx, x, y, w, h, r) {
    if (w < 2 * r) r = w / 2;
    if (h < 2 * r) r = h / 2;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  bindEvents() {
    // 键盘监听
    window.addEventListener('keydown', (e) => {
      // 正在展示帮助弹窗时优先按 ESC 或回车关闭
      if (!this.helpModal.classList.contains('hidden')) {
        if (e.key === 'Escape' || e.key === 'Enter') {
          this.closeHelp();
        }
        return;
      }

      switch (e.code) {
        case 'ArrowUp':
        case 'KeyW':
          e.preventDefault();
          this.handleDirectionInput({ x: 0, y: -1 });
          break;
        case 'ArrowDown':
        case 'KeyS':
          e.preventDefault();
          this.handleDirectionInput({ x: 0, y: 1 });
          break;
        case 'ArrowLeft':
        case 'KeyA':
          e.preventDefault();
          this.handleDirectionInput({ x: -1, y: 0 });
          break;
        case 'ArrowRight':
        case 'KeyD':
          e.preventDefault();
          this.handleDirectionInput({ x: 1, y: 0 });
          break;
        case 'Space':
          e.preventDefault();
          if (this.gameState === 'READY' || this.gameState === 'GAMEOVER') {
            this.startGame();
          } else {
            this.pauseGame();
          }
          break;
        case 'KeyR':
          e.preventDefault();
          this.startGame();
          break;
        case 'KeyM':
          this.toggleSound();
          break;
        case 'KeyT':
          this.toggleTheme();
          break;
      }
    });

    // 虚拟方向按键
    const dpadUp = document.getElementById('dpad-up');
    const dpadDown = document.getElementById('dpad-down');
    const dpadLeft = document.getElementById('dpad-left');
    const dpadRight = document.getElementById('dpad-right');
    const dpadPause = document.getElementById('dpad-pause');

    const bindTouchOrClick = (el, action) => {
      el.addEventListener('touchstart', (e) => {
        e.preventDefault();
        action();
      }, { passive: false });
      el.addEventListener('click', (e) => {
        e.preventDefault();
        action();
      });
    };

    bindTouchOrClick(dpadUp, () => this.handleDirectionInput({ x: 0, y: -1 }));
    bindTouchOrClick(dpadDown, () => this.handleDirectionInput({ x: 0, y: 1 }));
    bindTouchOrClick(dpadLeft, () => this.handleDirectionInput({ x: -1, y: 0 }));
    bindTouchOrClick(dpadRight, () => this.handleDirectionInput({ x: 1, y: 0 }));
    bindTouchOrClick(dpadPause, () => {
      if (this.gameState === 'READY' || this.gameState === 'GAMEOVER') {
        this.startGame();
      } else {
        this.pauseGame();
      }
    });

    // 移动端画布滑动手势支持
    let touchStartX = 0;
    let touchStartY = 0;
    this.canvas.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].screenX;
      touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });

    this.canvas.addEventListener('touchend', (e) => {
      const touchEndX = e.changedTouches[0].screenX;
      const touchEndY = e.changedTouches[0].screenY;
      const dx = touchEndX - touchStartX;
      const dy = touchEndY - touchStartY;
      const absDx = Math.abs(dx);
      const absDy = Math.abs(dy);

      if (Math.max(absDx, absDy) > 25) {
        if (absDx > absDy) {
          this.handleDirectionInput({ x: dx > 0 ? 1 : -1, y: 0 });
        } else {
          this.handleDirectionInput({ x: 0, y: dy > 0 ? 1 : -1 });
        }
      }
    }, { passive: true });

    // 主按钮 (开始 / 继续 / 再来一局)
    this.btnStart.addEventListener('click', () => {
      if (this.gameState === 'PAUSED') {
        this.resumeGame();
      } else {
        this.startGame();
      }
    });

    // 主题切换按钮
    this.btnTheme.addEventListener('click', () => this.toggleTheme());

    // 静音切换
    this.btnSound.addEventListener('click', () => this.toggleSound());

    // 模式切换
    const modeGroup = document.getElementById('mode-group');
    modeGroup.addEventListener('click', (e) => {
      if (e.target.classList.contains('toggle-btn')) {
        modeGroup.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        this.mode = e.target.dataset.mode;
        window.soundCtrl.playClick();
      }
    });

    // 速度切换
    const speedGroup = document.getElementById('speed-group');
    speedGroup.addEventListener('click', (e) => {
      if (e.target.classList.contains('toggle-btn')) {
        speedGroup.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        this.speedLevel = e.target.dataset.speed;
        window.soundCtrl.playClick();
      }
    });

    // 玩法帮助弹窗控制
    this.btnHelp.addEventListener('click', () => {
      this.helpModal.classList.remove('hidden');
      window.soundCtrl.playClick();
      if (this.gameState === 'PLAYING') {
        this.pauseGame();
      }
    });

    this.btnCloseHelp.addEventListener('click', () => this.closeHelp());
    this.btnModalOk.addEventListener('click', () => this.closeHelp());
    this.helpModal.addEventListener('click', (e) => {
      if (e.target === this.helpModal) this.closeHelp();
    });
  }

  closeHelp() {
    this.helpModal.classList.add('hidden');
    window.soundCtrl.playClick();
  }

  toggleSound() {
    const isMuted = window.soundCtrl.toggleMute();
    this.soundIcon.textContent = isMuted ? '🔇' : '🔊';
  }
}

// 页面加载完成后实例化游戏
window.addEventListener('DOMContentLoaded', () => {
  window.snakeGame = new VibrantSnakeGame();
});
