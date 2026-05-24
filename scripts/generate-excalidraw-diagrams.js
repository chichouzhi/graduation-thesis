const fs = require("fs");
const path = require("path");

const outputDir = path.join(
  process.cwd(),
  "毕设相关文件",
  "毕设流程文件",
  "excalidraw图表"
);

let elementSeq = 1;

function nextId(prefix) {
  const id = `${prefix}_${String(elementSeq).padStart(4, "0")}`;
  elementSeq += 1;
  return id;
}

function baseElement(type, x, y, width, height, extra = {}) {
  return {
    id: nextId(type),
    type,
    x,
    y,
    width,
    height,
    angle: 0,
    strokeColor: extra.strokeColor || "#1e1e1e",
    backgroundColor: extra.backgroundColor || "transparent",
    fillStyle: "solid",
    strokeWidth: extra.strokeWidth || 2,
    strokeStyle: extra.strokeStyle || "solid",
    roughness: 1,
    opacity: 100,
    groupIds: extra.groupIds || [],
    frameId: null,
    roundness: type === "rectangle" ? { type: 3 } : null,
    seed: elementSeq * 997,
    versionNonce: elementSeq * 7919,
    isDeleted: false,
    boundElements: null,
    updated: 1,
    link: null,
    locked: false
  };
}

function rectangle(x, y, width, height, options = {}) {
  return baseElement("rectangle", x, y, width, height, options);
}

function text(x, y, value, options = {}) {
  const fontSize = options.fontSize || 18;
  const width = options.width || 180;
  const lines = value.split("\n").length;
  return {
    ...baseElement("text", x, y, width, fontSize * lines * 1.25, {
      strokeColor: options.strokeColor || "#1e1e1e",
      backgroundColor: "transparent",
      groupIds: options.groupIds || []
    }),
    text: value,
    fontSize,
    fontFamily: 1,
    textAlign: options.textAlign || "center",
    verticalAlign: "middle",
    containerId: null,
    originalText: value,
    lineHeight: 1.25,
    baseline: Math.round(fontSize * lines)
  };
}

function node(label, x, y, width = 180, height = 70, options = {}) {
  const groupId = nextId("group");
  const shape = rectangle(x, y, width, height, {
    backgroundColor: options.backgroundColor || "#f5f5ff",
    strokeColor: options.strokeColor || "#1e1e1e",
    groupIds: [groupId]
  });
  const labelText = text(x + 10, y + height / 2 - 22, label, {
    width: width - 20,
    fontSize: options.fontSize || 18,
    groupIds: [groupId]
  });
  return { elements: [shape, labelText], anchor: { x: x + width / 2, y: y + height / 2 } };
}

function title(value) {
  return text(40, 20, value, { width: 620, fontSize: 28, textAlign: "left" });
}

function arrow(from, to, label, options = {}) {
  const start = options.start || from;
  const end = options.end || to;
  const points = [
    [0, 0],
    [end.x - start.x, end.y - start.y]
  ];
  const arrowElement = {
    ...baseElement("arrow", start.x, start.y, end.x - start.x, end.y - start.y, {
      strokeWidth: options.strokeWidth || 2,
      strokeColor: options.strokeColor || "#1e1e1e"
    }),
    points,
    lastCommittedPoint: null,
    startBinding: null,
    endBinding: null,
    startArrowhead: null,
    endArrowhead: "arrow",
    elbowed: false
  };
  if (!label) return [arrowElement];
  const labelX = start.x + (end.x - start.x) / 2 - 60;
  const labelY = start.y + (end.y - start.y) / 2 - 28;
  return [
    arrowElement,
    text(labelX, labelY, label, { width: 120, fontSize: 14 })
  ];
}

function buildDiagram(diagram) {
  elementSeq = 1;
  const elements = [title(diagram.title)];
  const anchors = {};

  for (const item of diagram.nodes) {
    if (item.kind === "label") {
      elements.push(text(item.x, item.y, item.label, { width: item.width || 260, fontSize: item.fontSize || 18, textAlign: item.textAlign || "center" }));
      continue;
    }
    const created = node(item.label, item.x, item.y, item.width, item.height, {
      backgroundColor: item.color,
      strokeColor: item.strokeColor,
      fontSize: item.fontSize
    });
    elements.push(...created.elements);
    anchors[item.id] = created.anchor;
  }

  for (const rel of diagram.edges) {
    const from = anchors[rel.from];
    const to = anchors[rel.to];
    if (!from || !to) {
      throw new Error(`${diagram.file}: missing anchor for ${rel.from} -> ${rel.to}`);
    }
    elements.push(...arrow(from, to, rel.label, { strokeWidth: rel.width }));
  }

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

const colors = {
  actor: "#ffffff",
  module: "#f5f5ff",
  service: "#e9f5ff",
  data: "#fff4e6",
  async: "#eaf8ef",
  external: "#f7f0ff",
  decision: "#fffbe6"
};

const diagrams = [
  {
    file: "图2-1-系统角色用例图.excalidraw",
    title: "图 2-1 系统角色用例图",
    nodes: [
      { id: "student", label: "学生", x: 60, y: 220, width: 120, color: colors.actor },
      { id: "teacher", label: "教师", x: 60, y: 390, width: 120, color: colors.actor },
      { id: "admin", label: "管理员", x: 60, y: 560, width: 120, color: colors.actor },
      { id: "profile", label: "画像维护", x: 290, y: 120, color: colors.module },
      { id: "recommend", label: "推荐查看\n解释信息", x: 530, y: 120, color: colors.module },
      { id: "apply", label: "志愿提交\n撤销调整", x: 770, y: 120, color: colors.module },
      { id: "topic", label: "题目管理\n提交审核", x: 290, y: 330, color: colors.module },
      { id: "decision", label: "志愿处理\n接受/拒绝", x: 530, y: 330, color: colors.module },
      { id: "assignment", label: "指导关系\n确认", x: 770, y: 330, color: colors.module },
      { id: "term", label: "学期与配置\n维护", x: 290, y: 540, color: colors.module },
      { id: "review", label: "题目审核", x: 530, y: 540, color: colors.module },
      { id: "taskboard", label: "过程看板\n问答/文档", x: 770, y: 540, color: colors.module }
    ],
    edges: [
      { from: "student", to: "profile" },
      { from: "student", to: "recommend" },
      { from: "student", to: "apply" },
      { from: "teacher", to: "topic" },
      { from: "teacher", to: "decision" },
      { from: "decision", to: "assignment" },
      { from: "admin", to: "term" },
      { from: "admin", to: "review" },
      { from: "assignment", to: "taskboard", label: "形成后使用" }
    ]
  },
  {
    file: "图2-2-系统功能模块结构图.excalidraw",
    title: "图 2-2 系统功能模块结构图",
    nodes: [
      { id: "system", label: "智能化毕业设计选题\n双向选择系统", x: 430, y: 90, width: 260, height: 80, color: "#ffffff" },
      { id: "core", label: "核心选题互选功能", x: 220, y: 230, width: 260, color: colors.service },
      { id: "assist", label: "选题后辅助功能", x: 650, y: 230, width: 260, color: colors.async },
      { id: "auth", label: "身份认证", x: 80, y: 380, color: colors.module },
      { id: "term", label: "学期管理", x: 300, y: 380, color: colors.module },
      { id: "topic", label: "课题管理\n题目画像", x: 520, y: 380, color: colors.module },
      { id: "recommend", label: "学生画像\n智能推荐", x: 740, y: 380, color: colors.module },
      { id: "selection", label: "志愿双向选择\n指导关系", x: 960, y: 380, color: colors.module },
      { id: "chat", label: "智能问答", x: 300, y: 540, color: colors.async },
      { id: "docs", label: "文档处理", x: 520, y: 540, color: colors.async },
      { id: "taskboard", label: "过程看板", x: 740, y: 540, color: colors.async }
    ],
    edges: [
      { from: "system", to: "core" },
      { from: "system", to: "assist" },
      { from: "core", to: "auth" },
      { from: "core", to: "term" },
      { from: "core", to: "topic" },
      { from: "core", to: "recommend" },
      { from: "core", to: "selection" },
      { from: "assist", to: "chat" },
      { from: "assist", to: "docs" },
      { from: "assist", to: "taskboard" }
    ]
  },
  {
    file: "图3-1-系统总体架构图.excalidraw",
    title: "图 3-1 系统总体架构图",
    nodes: [
      { id: "browser", label: "浏览器前端\nReact SPA", x: 80, y: 120, width: 210, color: colors.module },
      { id: "vite", label: "Vite Dev Server\n/API 代理", x: 410, y: 120, width: 210, color: colors.module },
      { id: "api", label: "Flask API\n认证/业务/入队", x: 740, y: 120, width: 230, color: colors.service },
      { id: "postgres", label: "PostgreSQL\n业务数据", x: 270, y: 340, width: 210, color: colors.data },
      { id: "redis", label: "Redis\n任务队列/缓存", x: 600, y: 340, width: 210, color: colors.data },
      { id: "worker", label: "Worker\n异步消费", x: 930, y: 340, width: 210, color: colors.async },
      { id: "llm", label: "LLM Adapter", x: 190, y: 560, color: colors.external },
      { id: "pdf", label: "PDF Adapter", x: 430, y: 560, color: colors.external },
      { id: "nlp", label: "NLP Adapter", x: 670, y: 560, color: colors.external },
      { id: "storage", label: "Storage Adapter", x: 910, y: 560, color: colors.external }
    ],
    edges: [
      { from: "browser", to: "vite", label: "HTTP" },
      { from: "vite", to: "api", label: "REST API" },
      { from: "api", to: "postgres", label: "读写" },
      { from: "api", to: "redis", label: "入队" },
      { from: "redis", to: "worker", label: "消费" },
      { from: "worker", to: "postgres", label: "回写" },
      { from: "worker", to: "llm" },
      { from: "worker", to: "pdf" },
      { from: "worker", to: "nlp" },
      { from: "worker", to: "storage" }
    ]
  },
  {
    file: "图3-2-后端分层架构图.excalidraw",
    title: "图 3-2 后端分层架构图",
    nodes: [
      { id: "api", label: "API 层\nHTTP 边界/DTO", x: 460, y: 100, width: 260, color: colors.service },
      { id: "service", label: "Service 层\n事务/业务规则", x: 460, y: 220, width: 260, color: colors.service },
      { id: "usecase", label: "Use Cases 层\n任务编排", x: 460, y: 340, width: 260, color: colors.module },
      { id: "task", label: "Task / Worker 层\n队列消费", x: 140, y: 340, width: 260, color: colors.async },
      { id: "adapter", label: "Adapter 层\nLLM/PDF/Storage", x: 780, y: 340, width: 260, color: colors.external },
      { id: "model", label: "Model 层\nSQLAlchemy 实体", x: 460, y: 470, width: 260, color: colors.data },
      { id: "common", label: "Common 基础层\n配置/错误/工具", x: 460, y: 600, width: 260, color: "#ffffff" }
    ],
    edges: [
      { from: "api", to: "service", label: "调用" },
      { from: "service", to: "usecase", label: "需要编排时" },
      { from: "service", to: "model", label: "持久化" },
      { from: "service", to: "task", label: "入队" },
      { from: "task", to: "usecase", label: "执行任务" },
      { from: "usecase", to: "adapter", label: "外部能力" },
      { from: "usecase", to: "model", label: "状态回写" },
      { from: "api", to: "common" },
      { from: "service", to: "common" },
      { from: "task", to: "common" }
    ]
  },
  {
    file: "图3-3-前端页面与模块结构图.excalidraw",
    title: "图 3-3 前端页面与模块结构图",
    nodes: [
      { id: "router", label: "React Router\n路由入口", x: 480, y: 90, width: 240, color: colors.service },
      { id: "login", label: "/login", x: 90, y: 230, color: colors.module },
      { id: "dash", label: "/app/dashboard", x: 310, y: 230, color: colors.module },
      { id: "topics", label: "/app/topics", x: 530, y: 230, color: colors.module },
      { id: "chat", label: "/app/chat", x: 750, y: 230, color: colors.module },
      { id: "docs", label: "/app/documents", x: 970, y: 230, color: colors.module },
      { id: "taskboard", label: "/app/taskboard", x: 530, y: 370, color: colors.module },
      { id: "features", label: "features\n业务页面模块", x: 220, y: 540, width: 220, color: colors.service },
      { id: "components", label: "components\n通用组件", x: 500, y: 540, width: 220, color: colors.service },
      { id: "lib", label: "lib\nAxios/Query/Auth", x: 780, y: 540, width: 220, color: colors.service }
    ],
    edges: [
      { from: "router", to: "login" },
      { from: "router", to: "dash" },
      { from: "router", to: "topics" },
      { from: "router", to: "chat" },
      { from: "router", to: "docs" },
      { from: "router", to: "taskboard" },
      { from: "dash", to: "features" },
      { from: "topics", to: "features" },
      { from: "chat", to: "features" },
      { from: "docs", to: "features" },
      { from: "features", to: "components" },
      { from: "features", to: "lib" }
    ]
  },
  {
    file: "图3-4-数据库ER图.excalidraw",
    title: "图 3-4 数据库 E-R 图",
    nodes: [
      { id: "users", label: "users\n用户/角色/画像", x: 500, y: 90, width: 220, color: colors.data },
      { id: "terms", label: "terms\n学期/选题窗口", x: 160, y: 230, width: 220, color: colors.data },
      { id: "topics", label: "topics\n课题/画像/容量", x: 500, y: 230, width: 220, color: colors.data },
      { id: "apps", label: "applications\n志愿申请/优先级", x: 840, y: 230, width: 240, color: colors.data },
      { id: "assign", label: "assignments\n指导关系", x: 500, y: 380, width: 220, color: colors.data },
      { id: "milestones", label: "milestones\n里程碑任务", x: 160, y: 520, width: 220, color: colors.data },
      { id: "convs", label: "conversations\n聊天会话", x: 500, y: 520, width: 220, color: colors.data },
      { id: "msgs", label: "messages\n聊天消息", x: 840, y: 520, width: 220, color: colors.data },
      { id: "chatjobs", label: "chat_jobs\n问答任务", x: 840, y: 670, width: 220, color: colors.data },
      { id: "doctasks", label: "document_tasks\n文档任务", x: 160, y: 670, width: 240, color: colors.data },
      { id: "artifacts", label: "document_artifacts\n文档工件", x: 500, y: 670, width: 250, color: colors.data }
    ],
    edges: [
      { from: "terms", to: "topics", label: "1:N" },
      { from: "users", to: "topics", label: "教师 1:N" },
      { from: "users", to: "apps", label: "学生 1:N" },
      { from: "topics", to: "apps", label: "1:N" },
      { from: "apps", to: "assign", label: "接受后生成" },
      { from: "users", to: "assign", label: "学生/教师" },
      { from: "topics", to: "assign", label: "1:N" },
      { from: "assign", to: "milestones", label: "过程管理" },
      { from: "users", to: "convs", label: "1:N" },
      { from: "convs", to: "msgs", label: "1:N" },
      { from: "msgs", to: "chatjobs", label: "触发" },
      { from: "users", to: "doctasks", label: "上传" },
      { from: "doctasks", to: "artifacts", label: "1:N" }
    ]
  },
  {
    file: "图3-5-异步任务状态流转图.excalidraw",
    title: "图 3-5 异步任务状态流转图",
    nodes: [
      { id: "pending", label: "pending\n待处理", x: 130, y: 170, color: colors.decision },
      { id: "running", label: "running\n处理中", x: 430, y: 170, color: colors.async },
      { id: "done", label: "done\n完成", x: 730, y: 90, color: colors.async },
      { id: "failed", label: "failed\n失败", x: 730, y: 250, color: "#ffecec" },
      { id: "chat", label: "chat_jobs\n智能问答", x: 80, y: 470, color: colors.module },
      { id: "pdf", label: "pdf_parse\nPDF 解析", x: 300, y: 470, color: colors.module },
      { id: "doc", label: "document_jobs\n文档分析", x: 520, y: 470, color: colors.module },
      { id: "keyword", label: "keyword_jobs\n题目画像", x: 740, y: 470, color: colors.module },
      { id: "reconcile", label: "reconcile_jobs\n内部对账", x: 960, y: 470, color: colors.module }
    ],
    edges: [
      { from: "pending", to: "running", label: "Worker 获取" },
      { from: "running", to: "done", label: "处理成功" },
      { from: "running", to: "failed", label: "异常/补偿" },
      { from: "chat", to: "pending" },
      { from: "pdf", to: "pending" },
      { from: "doc", to: "pending" },
      { from: "keyword", to: "pending" },
      { from: "reconcile", to: "pending" }
    ]
  },
  {
    file: "图4-1-用户登录与画像维护流程图.excalidraw",
    title: "图 4-1 用户登录与画像维护流程图",
    nodes: [
      { id: "login", label: "用户登录\n提交账号密码", x: 80, y: 240, color: colors.module },
      { id: "token", label: "保存访问令牌\n与认证态", x: 310, y: 240, color: colors.service },
      { id: "me", label: "请求 /users/me\n获取当前用户", x: 540, y: 240, color: colors.service },
      { id: "profile", label: "更新学生画像\n兴趣/技能/时间", x: 770, y: 240, color: colors.module },
      { id: "recommend", label: "进入推荐页面\n查看匹配结果", x: 1000, y: 240, color: colors.async }
    ],
    edges: [
      { from: "login", to: "token", label: "登录成功" },
      { from: "token", to: "me", label: "携带令牌" },
      { from: "me", to: "profile", label: "学生角色" },
      { from: "profile", to: "recommend", label: "画像作为输入" }
    ]
  },
  {
    file: "图4-2-课题画像生成流程图.excalidraw",
    title: "图 4-2 课题画像生成流程图",
    nodes: [
      { id: "teacher", label: "教师创建/更新题目", x: 60, y: 220, color: colors.actor },
      { id: "service", label: "TopicService\n保存题目", x: 300, y: 220, color: colors.service },
      { id: "tokenize", label: "同步分词\n基础文本信号", x: 540, y: 220, color: colors.module },
      { id: "queue", label: "keyword_jobs\n任务入队", x: 780, y: 220, color: colors.async },
      { id: "worker", label: "Worker 消费任务", x: 1020, y: 220, color: colors.async },
      { id: "usecase", label: "Use Case\n画像编排", x: 420, y: 420, color: colors.service },
      { id: "profile", label: "画像结果回写\n关键词/难度/能力/风险", x: 700, y: 420, width: 260, color: colors.data }
    ],
    edges: [
      { from: "teacher", to: "service" },
      { from: "service", to: "tokenize" },
      { from: "tokenize", to: "queue" },
      { from: "queue", to: "worker" },
      { from: "worker", to: "usecase" },
      { from: "usecase", to: "profile" }
    ]
  },
  {
    file: "图4-3-智能推荐计算流程图.excalidraw",
    title: "图 4-3 智能推荐计算流程图",
    nodes: [
      { id: "student", label: "学生画像\n兴趣/技能/关键词", x: 80, y: 170, width: 220, color: colors.module },
      { id: "topic", label: "题目画像\n关键词/能力/难度", x: 80, y: 350, width: 220, color: colors.module },
      { id: "norm", label: "关键词归一化", x: 390, y: 260, color: colors.service },
      { id: "jaccard", label: "Jaccard 打分\n关键词相似度", x: 630, y: 170, color: colors.service },
      { id: "ability", label: "能力匹配\n技能覆盖", x: 630, y: 350, color: colors.service },
      { id: "capacity", label: "容量状态\n难度适配", x: 870, y: 260, color: colors.decision },
      { id: "explain", label: "解释结果生成\n分数/理由/风险", x: 1110, y: 260, width: 220, color: colors.async }
    ],
    edges: [
      { from: "student", to: "norm" },
      { from: "topic", to: "norm" },
      { from: "norm", to: "jaccard" },
      { from: "norm", to: "ability" },
      { from: "jaccard", to: "capacity" },
      { from: "ability", to: "capacity" },
      { from: "capacity", to: "explain" }
    ]
  },
  {
    file: "图4-4-志愿填报与教师决策流程图.excalidraw",
    title: "图 4-4 志愿填报与教师决策流程图",
    nodes: [
      { id: "apply", label: "学生提交志愿\n第一/第二志愿", x: 60, y: 230, width: 220, color: colors.module },
      { id: "application", label: "创建 Application\npending", x: 340, y: 230, width: 220, color: colors.data },
      { id: "teacher", label: "教师查看申请\n结合画像判断", x: 620, y: 230, width: 220, color: colors.actor },
      { id: "accept", label: "接受申请", x: 900, y: 140, color: colors.async },
      { id: "reject", label: "拒绝申请", x: 900, y: 320, color: "#ffecec" },
      { id: "assignment", label: "生成 Assignment\n指导关系", x: 1140, y: 140, width: 220, color: colors.data },
      { id: "count", label: "更新 selected_count\n处理冲突申请", x: 1140, y: 320, width: 240, color: colors.data },
      { id: "reconcile", label: "触发 reconcile_jobs\n后台对账", x: 760, y: 500, width: 240, color: colors.async }
    ],
    edges: [
      { from: "apply", to: "application" },
      { from: "application", to: "teacher" },
      { from: "teacher", to: "accept" },
      { from: "teacher", to: "reject" },
      { from: "accept", to: "assignment" },
      { from: "accept", to: "count" },
      { from: "assignment", to: "reconcile" },
      { from: "count", to: "reconcile" }
    ]
  },
  {
    file: "图4-5-智能问答异步处理流程图.excalidraw",
    title: "图 4-5 智能问答异步处理流程图",
    nodes: [
      { id: "send", label: "用户发送消息", x: 60, y: 240, color: colors.module },
      { id: "messages", label: "创建 user 消息\nassistant 占位", x: 300, y: 240, width: 230, color: colors.data },
      { id: "job", label: "生成 ChatJob", x: 570, y: 240, color: colors.data },
      { id: "queue", label: "入队 chat_jobs", x: 810, y: 240, color: colors.async },
      { id: "worker", label: "Worker 消费", x: 1050, y: 240, color: colors.async },
      { id: "llm", label: "LLM Adapter\n生成回复", x: 700, y: 440, width: 220, color: colors.external },
      { id: "writeback", label: "回写 assistant 内容\n任务 done/failed", x: 980, y: 440, width: 250, color: colors.data }
    ],
    edges: [
      { from: "send", to: "messages" },
      { from: "messages", to: "job" },
      { from: "job", to: "queue" },
      { from: "queue", to: "worker" },
      { from: "worker", to: "llm" },
      { from: "llm", to: "writeback" }
    ]
  },
  {
    file: "图4-6-文献处理异步流程图.excalidraw",
    title: "图 4-6 文献处理异步流程图",
    nodes: [
      { id: "upload", label: "PDF 上传\n校验参数", x: 60, y: 220, color: colors.module },
      { id: "task", label: "创建 DocumentTask\npending", x: 300, y: 220, width: 240, color: colors.data },
      { id: "parseq", label: "入队 pdf_parse", x: 580, y: 220, color: colors.async },
      { id: "pdf", label: "PDF Adapter\n文本解析", x: 820, y: 220, width: 220, color: colors.external },
      { id: "artifact", label: "保存解析工件\nDocumentArtifact", x: 1080, y: 220, width: 240, color: colors.data },
      { id: "docq", label: "触发 document_jobs", x: 410, y: 430, width: 220, color: colors.async },
      { id: "analyze", label: "分块摘要/结论提取\n对比分析", x: 690, y: 430, width: 260, color: colors.service },
      { id: "writeback", label: "任务状态回写\n结果预览/错误信息", x: 1010, y: 430, width: 260, color: colors.data }
    ],
    edges: [
      { from: "upload", to: "task" },
      { from: "task", to: "parseq" },
      { from: "parseq", to: "pdf" },
      { from: "pdf", to: "artifact" },
      { from: "artifact", to: "docq" },
      { from: "docq", to: "analyze" },
      { from: "analyze", to: "writeback" }
    ]
  }
];

function writeReadme() {
  const lines = [
    "# Excalidraw 图表清单",
    "",
    "本目录由 `scripts/generate-excalidraw-diagrams.js` 生成，覆盖论文正文中前 13 个结构/流程/ER 类图片占位。图 4-7、图 4-8、图 5-1、图 5-2、图 5-3 为截图类占位，未生成 Excalidraw 替代图。",
    "",
    "| 图号 | 文件 |",
    "| --- | --- |"
  ];
  for (const diagram of diagrams) {
    const figure = diagram.title.replace(/^图\s*/, "图 ");
    lines.push(`| ${figure} | ${diagram.file} |`);
  }
  fs.writeFileSync(path.join(outputDir, "README.md"), `${lines.join("\n")}\n`, "utf8");
}

function main() {
  fs.mkdirSync(outputDir, { recursive: true });
  for (const diagram of diagrams) {
    const doc = buildDiagram(diagram);
    fs.writeFileSync(
      path.join(outputDir, diagram.file),
      `${JSON.stringify(doc, null, 2)}\n`,
      "utf8"
    );
  }
  writeReadme();
  console.log(`Generated ${diagrams.length} Excalidraw files in ${outputDir}`);
}

main();
