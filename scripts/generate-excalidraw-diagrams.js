const fs = require("fs");
const path = require("path");

const outputDir = path.join(
  process.cwd(),
  "毕设相关文件",
  "毕设流程文件",
  "excalidraw图表"
);

const palette = {
  ink: "#1e1e1e",
  softInk: "#4a4a4a",
  paper: "#ffffff",
  gray1: "#f8f8f8",
  gray2: "#eeeeee",
  gray3: "#dddddd",
  gray4: "#f3f3f3"
};

let elementSeq = 1;

function nextId(prefix) {
  const id = `${prefix}_${String(elementSeq).padStart(4, "0")}`;
  elementSeq += 1;
  return id;
}

function base(type, x, y, width, height, options = {}) {
  return {
    id: nextId(type),
    type,
    x,
    y,
    width,
    height,
    angle: 0,
    strokeColor: options.strokeColor || palette.ink,
    backgroundColor: options.backgroundColor || "transparent",
    fillStyle: "solid",
    strokeWidth: options.strokeWidth || 1,
    strokeStyle: options.strokeStyle || "solid",
    roughness: options.roughness ?? 0,
    opacity: 100,
    groupIds: options.groupIds || [],
    frameId: null,
    roundness: options.roundness ?? null,
    seed: elementSeq * 1009,
    versionNonce: elementSeq * 7919,
    isDeleted: false,
    boundElements: null,
    updated: 1,
    link: null,
    locked: false
  };
}

function rect(x, y, width, height, options = {}) {
  return base("rectangle", x, y, width, height, {
    ...options,
    roundness: options.roundness ?? { type: 3 }
  });
}

function ellipse(x, y, width, height, options = {}) {
  return base("ellipse", x, y, width, height, options);
}

function text(x, y, value, options = {}) {
  const fontSize = options.fontSize || 16;
  const width = options.width || 180;
  const lineCount = value.split("\n").length;
  return {
    ...base("text", x, y, width, options.height || fontSize * lineCount * 1.3, {
      strokeColor: options.strokeColor || palette.ink,
      backgroundColor: "transparent",
      groupIds: options.groupIds || []
    }),
    text: value,
    fontSize,
    fontFamily: 1,
    textAlign: options.textAlign || "center",
    verticalAlign: options.verticalAlign || "middle",
    containerId: null,
    originalText: value,
    lineHeight: 1.25,
    baseline: Math.round(fontSize * lineCount)
  };
}

function line(points, options = {}) {
  const [first, ...rest] = points;
  const last = points[points.length - 1];
  return {
    ...base("line", first[0], first[1], last[0] - first[0], last[1] - first[1], options),
    points: [[0, 0], ...rest.map(([x, y]) => [x - first[0], y - first[1]])],
    lastCommittedPoint: null,
    startBinding: null,
    endBinding: null,
    startArrowhead: null,
    endArrowhead: null,
    elbowed: true
  };
}

function arrow(points, options = {}) {
  const [first, ...rest] = points;
  const last = points[points.length - 1];
  return {
    ...base("arrow", first[0], first[1], last[0] - first[0], last[1] - first[1], {
      strokeWidth: options.strokeWidth || 1,
      strokeColor: options.strokeColor || palette.ink,
      strokeStyle: options.strokeStyle || "solid"
    }),
    points: [[0, 0], ...rest.map(([x, y]) => [x - first[0], y - first[1]])],
    lastCommittedPoint: null,
    startBinding: null,
    endBinding: null,
    startArrowhead: options.startArrowhead || null,
    endArrowhead: options.endArrowhead || "arrow",
    elbowed: true
  };
}

function labelAlong(points, value, options = {}) {
  if (!value) return [];
  const mid = points[Math.floor(points.length / 2)];
  return [text(mid[0] - 55, mid[1] - 26, value, { width: 110, fontSize: 12, strokeColor: palette.softInk })];
}

function connector(points, label, options = {}) {
  return [arrow(points, options), ...labelAlong(points, label, options)];
}

function relation(points, label, options = {}) {
  return [line(points, options), ...labelAlong(points, label, options)];
}

function title(value) {
  return text(40, 26, value, {
    width: 1120,
    fontSize: 22,
    textAlign: "center",
    strokeColor: palette.ink
  });
}

function caption(value, x, y, width = 240) {
  return text(x, y, value, {
    width,
    fontSize: 14,
    textAlign: "center",
    strokeColor: palette.softInk
  });
}

function box(label, x, y, width, height, options = {}) {
  const groupId = nextId("group");
  const elements = [
    rect(x, y, width, height, {
      backgroundColor: options.fill || palette.paper,
      strokeColor: options.stroke || palette.ink,
      strokeWidth: options.strokeWidth || 1,
      groupIds: [groupId]
    }),
    text(x + 8, y + height / 2 - (options.textHeight || 20), label, {
      width: width - 16,
      fontSize: options.fontSize || 15,
      groupIds: [groupId]
    })
  ];
  return {
    elements,
    left: [x, y + height / 2],
    right: [x + width, y + height / 2],
    top: [x + width / 2, y],
    bottom: [x + width / 2, y + height],
    center: [x + width / 2, y + height / 2],
    x,
    y,
    width,
    height
  };
}

function oval(label, x, y, width, height, options = {}) {
  const groupId = nextId("group");
  const elements = [
    ellipse(x, y, width, height, {
      backgroundColor: options.fill || palette.paper,
      strokeColor: options.stroke || palette.ink,
      strokeWidth: 1,
      groupIds: [groupId]
    }),
    text(x + 10, y + height / 2 - 18, label, {
      width: width - 20,
      fontSize: options.fontSize || 14,
      groupIds: [groupId]
    })
  ];
  return {
    elements,
    left: [x, y + height / 2],
    right: [x + width, y + height / 2],
    top: [x + width / 2, y],
    bottom: [x + width / 2, y + height],
    center: [x + width / 2, y + height / 2]
  };
}

function groupBox(label, x, y, width, height, options = {}) {
  return [
    rect(x, y, width, height, {
      backgroundColor: options.fill || palette.gray1,
      strokeColor: options.stroke || palette.ink,
      strokeWidth: 1,
      strokeStyle: options.strokeStyle || "solid"
    }),
    text(x + 12, y + 10, label, {
      width: width - 24,
      fontSize: options.fontSize || 15,
      textAlign: "left",
      verticalAlign: "top",
      strokeColor: palette.ink
    })
  ];
}

function tableEntity(name, rows, x, y, width = 210) {
  const rowHeight = 28;
  const headerHeight = 36;
  const height = headerHeight + rows.length * rowHeight;
  const elements = [
    rect(x, y, width, height, { backgroundColor: palette.paper, strokeWidth: 1 }),
    rect(x, y, width, headerHeight, { backgroundColor: palette.gray2, strokeWidth: 1, roundness: null }),
    text(x + 8, y + 8, name, { width: width - 16, fontSize: 15, textAlign: "center" })
  ];
  rows.forEach((row, index) => {
    const rowY = y + headerHeight + index * rowHeight;
    elements.push(line([[x, rowY], [x + width, rowY]], { strokeColor: palette.gray3 }));
    elements.push(text(x + 10, rowY + 6, row, { width: width - 20, fontSize: 12, textAlign: "left" }));
  });
  return {
    elements,
    left: [x, y + height / 2],
    right: [x + width, y + height / 2],
    top: [x + width / 2, y],
    bottom: [x + width / 2, y + height],
    center: [x + width / 2, y + height / 2],
    x,
    y,
    width,
    height
  };
}

function actor(label, x, y) {
  const groupId = nextId("group");
  const cx = x + 34;
  const elements = [
    ellipse(cx - 14, y, 28, 28, { groupIds: [groupId] }),
    line([[cx, y + 28], [cx, y + 72]], { groupIds: [groupId] }),
    line([[cx - 30, y + 42], [cx + 30, y + 42]], { groupIds: [groupId] }),
    line([[cx, y + 72], [cx - 28, y + 112]], { groupIds: [groupId] }),
    line([[cx, y + 72], [cx + 28, y + 112]], { groupIds: [groupId] }),
    text(x - 24, y + 120, label, { width: 116, fontSize: 14, groupIds: [groupId] })
  ];
  return {
    elements,
    right: [x + 78, y + 58],
    left: [x - 10, y + 58],
    center: [cx, y + 58]
  };
}

function addAll(target, ...items) {
  for (const item of items) {
    if (Array.isArray(item)) target.push(...item);
    else if (item && Array.isArray(item.elements)) target.push(...item.elements);
    else if (item) target.push(item);
  }
}

function diagramDoc(name, build) {
  elementSeq = 1;
  const elements = [title(name)];
  build(elements);
  return {
    type: "excalidraw",
    version: 2,
    source: "claude-code-excalidraw-prompt",
    elements,
    appState: {
      gridSize: 20,
      viewBackgroundColor: "#ffffff"
    },
    files: {}
  };
}

const diagrams = [
  {
    file: "图2-1-系统角色用例图.excalidraw",
    title: "图 2-1 系统角色用例图",
    build(elements) {
      addAll(elements, groupBox("智能化毕业设计选题双向选择系统", 230, 100, 740, 540));
      const student = actor("学生", 70, 190);
      const teacher = actor("教师", 70, 420);
      const admin = actor("管理员", 1020, 305);
      addAll(elements, student, teacher, admin);

      const useCases = {
        profile: oval("维护学生画像", 290, 155, 170, 54),
        recommend: oval("查看推荐与解释", 515, 155, 170, 54),
        apply: oval("提交/调整志愿", 740, 155, 170, 54),
        topic: oval("创建与维护题目", 290, 310, 170, 54),
        portrait: oval("查看题目画像", 515, 310, 170, 54),
        decide: oval("处理学生志愿", 740, 310, 170, 54),
        term: oval("维护学期配置", 290, 465, 170, 54),
        review: oval("审核教师题目", 515, 465, 170, 54),
        board: oval("查看过程看板", 740, 465, 170, 54)
      };
      Object.values(useCases).forEach((item) => addAll(elements, item));
      addAll(elements,
        caption("学生端", 405, 115, 150),
        caption("教师端", 405, 270, 150),
        caption("管理与过程支撑", 500, 425, 200),
        relation([student.right, useCases.profile.left]),
        relation([student.right, [210, 240], [515, 240], useCases.recommend.bottom]),
        relation([student.right, [210, 255], [740, 255], useCases.apply.bottom]),
        relation([teacher.right, useCases.topic.left]),
        relation([teacher.right, [210, 455], [515, 385], useCases.portrait.bottom]),
        relation([teacher.right, [210, 470], [740, 385], useCases.decide.bottom]),
        relation([admin.left, [970, 505], useCases.term.right]),
        relation([admin.left, [970, 505], useCases.review.right]),
        relation([admin.left, [970, 505], useCases.board.right])
      );
    }
  },
  {
    file: "图2-2-系统功能模块结构图.excalidraw",
    title: "图 2-2 系统功能模块结构图",
    build(elements) {
      const root = box("智能化毕业设计选题双向选择系统", 430, 95, 340, 54, { fill: palette.gray2, fontSize: 16 });
      const core = box("核心选题互选功能", 170, 205, 260, 50, { fill: palette.gray1 });
      const assist = box("选题后辅助功能", 470, 205, 260, 50, { fill: palette.gray1 });
      const baseLayer = box("基础支撑功能", 770, 205, 260, 50, { fill: palette.gray1 });
      addAll(elements, root, core, assist, baseLayer);

      const coreItems = [
        box("课题管理", 70, 330, 150, 48),
        box("题目画像", 245, 330, 150, 48),
        box("学生画像", 420, 330, 150, 48),
        box("智能推荐", 595, 330, 150, 48),
        box("志愿双向选择", 770, 330, 170, 48),
        box("指导关系", 965, 330, 150, 48)
      ];
      const assistItems = [
        box("智能问答", 245, 485, 170, 48),
        box("文档处理", 515, 485, 170, 48),
        box("过程看板", 785, 485, 170, 48)
      ];
      const baseItems = [
        box("身份认证", 245, 610, 170, 48),
        box("学期管理", 515, 610, 170, 48),
        box("系统配置", 785, 610, 170, 48)
      ];
      [...coreItems, ...assistItems, ...baseItems].forEach((item) => addAll(elements, item));
      addAll(elements,
        relation([root.bottom, [root.bottom[0], 175], core.top]),
        relation([root.bottom, [root.bottom[0], 175], assist.top]),
        relation([root.bottom, [root.bottom[0], 175], baseLayer.top])
      );
      coreItems.forEach((item) => addAll(elements, relation([core.bottom, [core.bottom[0], 300], item.top])));
      assistItems.forEach((item) => addAll(elements, relation([assist.bottom, [assist.bottom[0], 455], item.top])));
      baseItems.forEach((item) => addAll(elements, relation([baseLayer.bottom, [baseLayer.bottom[0], 580], item.top])));
    }
  },
  {
    file: "图3-1-系统总体架构图.excalidraw",
    title: "图 3-1 系统总体架构图",
    build(elements) {
      const lanes = [
        ["访问层", 95],
        ["应用服务层", 230],
        ["数据与队列层", 365],
        ["外部能力适配层", 505]
      ];
      lanes.forEach(([label, y]) => addAll(elements, groupBox(label, 70, y, 1060, 95, { fill: palette.gray1 })));
      const browser = box("浏览器前端\nReact SPA", 145, 125, 200, 55);
      const vite = box("Vite 代理\n/API 转发", 500, 125, 200, 55);
      const api = box("Flask API\n认证 / 业务 / 入队", 500, 260, 230, 55, { fill: palette.gray2 });
      const worker = box("Worker\n异步任务消费", 820, 260, 220, 55, { fill: palette.gray2 });
      const postgres = box("PostgreSQL\n业务数据持久化", 260, 395, 230, 55);
      const redis = box("Redis\n任务队列与缓存", 690, 395, 230, 55);
      const adapters = [
        box("LLM Adapter", 150, 535, 180, 50),
        box("PDF Adapter", 390, 535, 180, 50),
        box("NLP Adapter", 630, 535, 180, 50),
        box("Storage Adapter", 870, 535, 180, 50)
      ];
      [browser, vite, api, worker, postgres, redis, ...adapters].forEach((item) => addAll(elements, item));
      addAll(elements,
        connector([browser.right, vite.left], "HTTP"),
        connector([vite.right, api.left], "REST API"),
        connector([api.bottom, [api.bottom[0], 360], postgres.top], "读写"),
        connector([api.right, [780, 287], worker.left], "任务分发"),
        connector([api.bottom, [api.bottom[0], 360], redis.top], "入队"),
        connector([redis.top, [redis.top[0], 340], worker.bottom], "消费"),
        connector([worker.bottom, [worker.bottom[0], 485], adapters[0].top]),
        connector([worker.bottom, [worker.bottom[0], 485], adapters[1].top]),
        connector([worker.bottom, [worker.bottom[0], 485], adapters[2].top]),
        connector([worker.bottom, [worker.bottom[0], 485], adapters[3].top]),
        connector([worker.left, [620, 287], [620, 395], postgres.right], "回写")
      );
    }
  },
  {
    file: "图3-2-后端分层架构图.excalidraw",
    title: "图 3-2 后端分层架构图",
    build(elements) {
      const layers = [
        box("API 层\nHTTP 边界 / 参数校验 / DTO", 385, 105, 430, 58, { fill: palette.gray2 }),
        box("Service 层\n业务规则 / 事务 / 入队决策", 385, 205, 430, 58),
        box("Use Cases 层\nLLM 与文档任务编排", 385, 305, 430, 58),
        box("Model 层\nSQLAlchemy 实体 / Repository 查询", 385, 505, 430, 58),
        box("Common 基础层\n配置 / 错误结构 / 工具函数", 385, 610, 430, 58, { fill: palette.gray1 })
      ];
      const task = box("Task / Worker 层\n队列消费 / 状态回写", 95, 305, 230, 58, { fill: palette.gray1 });
      const adapter = box("Adapter 层\nLLM / PDF / NLP / Storage", 875, 305, 250, 58, { fill: palette.gray1 });
      [...layers, task, adapter].forEach((item) => addAll(elements, item));
      addAll(elements,
        connector([layers[0].bottom, layers[1].top], "调用"),
        connector([layers[1].bottom, layers[2].top], "编排任务"),
        connector([layers[1].bottom, [layers[1].bottom[0], 480], layers[3].top], "持久化"),
        connector([layers[2].right, adapter.left], "外部能力"),
        connector([layers[1].left, task.right], "提交任务"),
        connector([task.right, layers[2].left], "执行编排"),
        connector([layers[2].bottom, layers[3].top], "回写状态"),
        connector([layers[3].bottom, layers[4].top]),
        connector([task.bottom, [task.bottom[0], 590], layers[4].left]),
        connector([adapter.bottom, [adapter.bottom[0], 590], layers[4].right])
      );
    }
  },
  {
    file: "图3-3-前端页面与模块结构图.excalidraw",
    title: "图 3-3 前端页面与模块结构图",
    build(elements) {
      addAll(elements,
        groupBox("页面路由层", 70, 105, 1060, 145),
        groupBox("业务功能层", 70, 300, 1060, 145),
        groupBox("基础共享层", 70, 495, 1060, 145)
      );
      const router = box("React Router\n/app 布局与鉴权", 470, 140, 260, 55, { fill: palette.gray2 });
      const pages = [
        box("/login", 110, 210, 145, 45),
        box("/app/dashboard", 285, 210, 160, 45),
        box("/app/topics", 475, 210, 145, 45),
        box("/app/chat", 650, 210, 145, 45),
        box("/app/documents", 825, 210, 160, 45),
        box("/app/taskboard", 1015, 210, 160, 45)
      ];
      const features = [
        box("auth feature", 120, 345, 150, 45),
        box("topics feature", 330, 345, 150, 45),
        box("selection feature", 540, 345, 170, 45),
        box("chat / documents", 760, 345, 180, 45),
        box("taskboard feature", 980, 345, 170, 45)
      ];
      const shared = [
        box("components\n通用组件", 240, 545, 190, 50),
        box("lib/api\nAxios / Error", 505, 545, 190, 50),
        box("query/store\nTanStack / Zustand", 770, 545, 220, 50)
      ];
      [router, ...pages, ...features, ...shared].forEach((item) => addAll(elements, item));
      pages.forEach((item) => addAll(elements, relation([router.bottom, [router.bottom[0], 205], item.top])));
      features.forEach((item) => addAll(elements, relation([pages[2].bottom, [pages[2].bottom[0], 320], item.top])));
      features.forEach((item, index) => addAll(elements, relation([item.bottom, [item.bottom[0], 510], shared[index % shared.length].top])));
    }
  },
  {
    file: "图3-4-数据库ER图.excalidraw",
    title: "图 3-4 数据库 E-R 图",
    build(elements) {
      const users = tableEntity("users", ["PK id", "role", "display_name", "student_profile"], 480, 95);
      const terms = tableEntity("terms", ["PK id", "name", "selection_window", "llm_config"], 90, 235);
      const topics = tableEntity("topics", ["PK id", "FK term_id", "FK teacher_id", "portrait_json", "selected_count"], 480, 235, 230);
      const apps = tableEntity("applications", ["PK id", "FK student_id", "FK topic_id", "priority", "status"], 850, 235, 230);
      const assign = tableEntity("assignments", ["PK id", "FK topic_id", "FK student_id", "FK teacher_id"], 480, 440, 230);
      const milestones = tableEntity("milestones", ["PK id", "FK assignment_id", "title", "status"], 90, 550);
      const convs = tableEntity("conversations", ["PK id", "FK user_id", "FK term_id"], 350, 550);
      const msgs = tableEntity("messages", ["PK id", "FK conversation_id", "role", "content"], 610, 550);
      const jobs = tableEntity("chat_jobs", ["PK id", "FK message_id", "status"], 870, 550);
      const doct = tableEntity("document_tasks", ["PK id", "FK user_id", "status", "task_type"], 220, 680, 230);
      const art = tableEntity("document_artifacts", ["PK id", "FK document_task_id", "artifact_type"], 610, 680, 250);
      [users, terms, topics, apps, assign, milestones, convs, msgs, jobs, doct, art].forEach((item) => addAll(elements, item));
      addAll(elements,
        relation([terms.right, topics.left], "1:N"),
        relation([users.bottom, topics.top], "教师"),
        relation([users.right, [830, users.center[1]], apps.top], "学生"),
        relation([topics.right, apps.left], "1:N"),
        relation([apps.bottom, [apps.bottom[0], 410], assign.right], "接受后"),
        relation([topics.bottom, assign.top], "1:N"),
        relation([assign.left, [310, assign.center[1]], milestones.top], "1:N"),
        relation([users.bottom, [users.bottom[0], 520], convs.top], "1:N"),
        relation([convs.right, msgs.left], "1:N"),
        relation([msgs.right, jobs.left], "触发"),
        relation([users.left, [330, users.center[1]], doct.top], "上传"),
        relation([doct.right, art.left], "1:N")
      );
    }
  },
  {
    file: "图3-5-异步任务状态流转图.excalidraw",
    title: "图 3-5 异步任务状态流转图",
    build(elements) {
      const pending = box("pending\n待处理", 220, 170, 180, 60, { fill: palette.gray1 });
      const running = box("running\n处理中", 510, 170, 180, 60, { fill: palette.gray2 });
      const done = box("done\n完成", 800, 105, 180, 60);
      const failed = box("failed\n失败", 800, 245, 180, 60);
      [pending, running, done, failed].forEach((item) => addAll(elements, item));
      addAll(elements,
        connector([pending.right, running.left], "Worker 获取"),
        connector([running.right, [745, 200], [745, 135], done.left], "成功"),
        connector([running.right, [745, 200], [745, 275], failed.left], "异常")
      );
      addAll(elements, groupBox("任务队列类型", 105, 430, 990, 150));
      const queues = [
        box("chat_jobs\n智能问答", 145, 500, 160, 50),
        box("pdf_parse\nPDF 解析", 335, 500, 160, 50),
        box("document_jobs\n文档分析", 525, 500, 180, 50),
        box("keyword_jobs\n题目画像", 735, 500, 170, 50),
        box("reconcile_jobs\n内部对账", 935, 500, 170, 50)
      ];
      queues.forEach((item) => addAll(elements, item, connector([item.top, [item.top[0], 390], pending.bottom])));
    }
  },
  {
    file: "图4-1-用户登录与画像维护流程图.excalidraw",
    title: "图 4-1 用户登录与画像维护流程图",
    build(elements) {
      addAll(elements,
        groupBox("前端", 70, 110, 1060, 105),
        groupBox("后端 API", 70, 265, 1060, 105),
        groupBox("业务结果", 70, 420, 1060, 105)
      );
      const login = box("登录表单\n账号密码", 120, 140, 170, 48);
      const token = box("保存令牌\n认证状态", 370, 140, 170, 48);
      const me = box("请求 /users/me\n获取当前用户", 620, 295, 210, 48);
      const update = box("更新学生画像\n兴趣/技能/时间", 370, 295, 210, 48);
      const recommend = box("进入推荐页面\n查看匹配解释", 620, 450, 220, 48);
      [login, token, me, update, recommend].forEach((item) => addAll(elements, item));
      addAll(elements,
        connector([login.right, token.left], "登录成功"),
        connector([token.right, [555, 164], [555, 319], me.left], "携带令牌"),
        connector([me.left, update.right], "学生角色"),
        connector([update.bottom, [475, 405], recommend.top], "画像输入")
      );
    }
  },
  {
    file: "图4-2-课题画像生成流程图.excalidraw",
    title: "图 4-2 课题画像生成流程图",
    build(elements) {
      addAll(elements,
        groupBox("教师端", 70, 110, 1060, 90),
        groupBox("同步事务", 70, 250, 1060, 90),
        groupBox("异步画像生成", 70, 390, 1060, 125)
      );
      const a = box("创建/更新题目", 120, 135, 170, 45);
      const b = box("TopicService\n保存题目", 360, 275, 185, 45);
      const c = box("同步分词\n基础文本信号", 610, 275, 185, 45);
      const d = box("keyword_jobs\n提交队列", 850, 275, 185, 45);
      const e = box("Worker 消费", 220, 430, 170, 45);
      const f = box("Use Case\n生成题目画像", 500, 430, 190, 45);
      const g = box("画像结果回写\n关键词/难度/能力/风险", 780, 430, 250, 45);
      [a, b, c, d, e, f, g].forEach((item) => addAll(elements, item));
      addAll(elements,
        connector([a.bottom, [205, 250], b.left]),
        connector([b.right, c.left]),
        connector([c.right, d.left]),
        connector([d.bottom, [943, 380], e.top]),
        connector([e.right, f.left]),
        connector([f.right, g.left])
      );
    }
  },
  {
    file: "图4-3-智能推荐计算流程图.excalidraw",
    title: "图 4-3 智能推荐计算流程图",
    build(elements) {
      const student = box("学生画像\n兴趣 / 技能 / 关键词", 95, 170, 230, 58);
      const topic = box("题目画像\n关键词 / 能力 / 难度", 95, 330, 230, 58);
      const norm = box("特征归一化\n去重 / 分词 / 标准化", 420, 250, 230, 58, { fill: palette.gray2 });
      const score1 = box("关键词相似度\nJaccard 打分", 745, 150, 210, 55);
      const score2 = box("能力匹配\n技能覆盖", 745, 250, 210, 55);
      const score3 = box("难度与容量\n适配修正", 745, 350, 210, 55);
      const explain = box("推荐结果\n分数 + 可解释理由", 1010, 250, 230, 58, { fill: palette.gray1 });
      [student, topic, norm, score1, score2, score3, explain].forEach((item) => addAll(elements, item));
      addAll(elements,
        connector([student.right, [370, 199], norm.left]),
        connector([topic.right, [370, 359], norm.left]),
        connector([norm.right, score1.left]),
        connector([norm.right, score2.left]),
        connector([norm.right, score3.left]),
        connector([score1.right, [990, 178], explain.left]),
        connector([score2.right, explain.left]),
        connector([score3.right, [990, 378], explain.left])
      );
    }
  },
  {
    file: "图4-4-志愿填报与教师决策流程图.excalidraw",
    title: "图 4-4 志愿填报与教师决策流程图",
    build(elements) {
      addAll(elements,
        groupBox("学生", 70, 120, 1060, 80),
        groupBox("教师决策", 70, 260, 1060, 130),
        groupBox("事务与后台对账", 70, 455, 1060, 105)
      );
      const submit = box("提交志愿\n第一/第二志愿", 130, 145, 200, 45);
      const app = box("Application\n状态 pending", 455, 145, 210, 45);
      const review = box("查看申请\n结合画像与优先级", 130, 305, 220, 45);
      const accept = box("接受申请", 480, 275, 170, 45);
      const reject = box("拒绝申请", 480, 345, 170, 45);
      const assignment = box("生成 Assignment\n指导关系", 735, 480, 220, 45);
      const count = box("更新 selected_count\n处理冲突申请", 735, 535, 230, 45);
      const reconcile = box("reconcile_jobs\n后台对账", 1010, 508, 180, 45);
      [submit, app, review, accept, reject, assignment, count, reconcile].forEach((item) => addAll(elements, item));
      addAll(elements,
        connector([submit.right, app.left]),
        connector([app.bottom, [560, 250], review.right]),
        connector([review.right, accept.left], "通过"),
        connector([review.right, [430, 328], [430, 368], reject.left], "不通过"),
        connector([accept.bottom, [565, 455], assignment.left]),
        connector([accept.bottom, [565, 455], count.left]),
        connector([assignment.right, reconcile.left]),
        connector([count.right, reconcile.left])
      );
    }
  },
  {
    file: "图4-5-智能问答异步处理流程图.excalidraw",
    title: "图 4-5 智能问答异步处理流程图",
    build(elements) {
      addAll(elements,
        groupBox("前端", 70, 110, 1060, 80),
        groupBox("API / 数据库", 70, 245, 1060, 110),
        groupBox("异步 Worker", 70, 420, 1060, 110)
      );
      const send = box("用户发送消息", 120, 135, 170, 45);
      const placeholder = box("创建 user 消息\nassistant 占位", 350, 275, 230, 50);
      const job = box("生成 ChatJob", 650, 275, 170, 50);
      const queue = box("入队 chat_jobs", 900, 275, 180, 50);
      const worker = box("Worker 消费", 210, 455, 170, 45);
      const llm = box("LLM Adapter\n生成回复", 510, 455, 190, 45);
      const write = box("回写 assistant 内容\n任务 done / failed", 820, 455, 240, 45);
      [send, placeholder, job, queue, worker, llm, write].forEach((item) => addAll(elements, item));
      addAll(elements,
        connector([send.bottom, [205, 245], placeholder.left]),
        connector([placeholder.right, job.left]),
        connector([job.right, queue.left]),
        connector([queue.bottom, [990, 405], worker.top]),
        connector([worker.right, llm.left]),
        connector([llm.right, write.left])
      );
    }
  },
  {
    file: "图4-6-文献处理异步流程图.excalidraw",
    title: "图 4-6 文献处理异步流程图",
    build(elements) {
      addAll(elements,
        groupBox("上传受理", 70, 105, 1060, 100),
        groupBox("PDF 解析阶段", 70, 260, 1060, 105),
        groupBox("文档分析阶段", 70, 430, 1060, 120)
      );
      const upload = box("PDF 上传\n参数校验", 120, 135, 180, 45);
      const task = box("创建 DocumentTask\n状态 pending", 400, 135, 230, 45);
      const parseQ = box("入队 pdf_parse", 720, 135, 190, 45);
      const pdf = box("PDF Adapter\n提取文本", 210, 295, 190, 45);
      const artifact = box("保存 DocumentArtifact\n解析工件", 520, 295, 240, 45);
      const docQ = box("触发 document_jobs", 850, 295, 210, 45);
      const analyze = box("分块摘要 / 结论提取\n对比分析", 310, 470, 260, 50);
      const write = box("任务状态回写\n结果预览 / 错误信息", 720, 470, 260, 50);
      [upload, task, parseQ, pdf, artifact, docQ, analyze, write].forEach((item) => addAll(elements, item));
      addAll(elements,
        connector([upload.right, task.left]),
        connector([task.right, parseQ.left]),
        connector([parseQ.bottom, [815, 250], pdf.top]),
        connector([pdf.right, artifact.left]),
        connector([artifact.right, docQ.left]),
        connector([docQ.bottom, [955, 420], analyze.top]),
        connector([analyze.right, write.left])
      );
    }
  }
];

function writeReadme() {
  const lines = [
    "# Excalidraw 图表清单",
    "",
    "本目录由 `scripts/generate-excalidraw-diagrams.js` 生成。当前版本采用毕业论文正文插图风格：黑白灰配色、低手绘感、分层布局、泳道流程、表格化 E-R 图和正交连线。",
    "",
    "| 图号 | 文件 |",
    "| --- | --- |"
  ];
  diagrams.forEach((diagram) => {
    lines.push(`| ${diagram.title} | ${diagram.file} |`);
  });
  fs.writeFileSync(path.join(outputDir, "README.md"), `${lines.join("\n")}\n`, "utf8");
}

function main() {
  fs.mkdirSync(outputDir, { recursive: true });
  diagrams.forEach((diagram) => {
    const doc = diagramDoc(diagram.title, diagram.build);
    fs.writeFileSync(
      path.join(outputDir, diagram.file),
      `${JSON.stringify(doc, null, 2)}\n`,
      "utf8"
    );
  });
  writeReadme();
  console.log(`Generated ${diagrams.length} thesis-style Excalidraw files in ${outputDir}`);
}

main();
