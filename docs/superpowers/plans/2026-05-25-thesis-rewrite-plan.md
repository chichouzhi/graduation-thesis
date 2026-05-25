# Thesis Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a Word-ready reconstructed thesis text that preserves the existing undergraduate software-engineering thesis structure while improving academic logic, topic focus, and formal Chinese expression.

**Architecture:** The rewrite keeps the original six-chapter framework, image placeholders, figure captions, and reference numbering. Each chapter is rewritten around the central business loop: topic portrait, student portrait, explainable recommendation, voluntary application, teacher decision, assignment formation, and post-selection support.

**Tech Stack:** Plain text thesis file, PowerShell verification commands, no source-code changes.

---

### Task 1: Confirm Source Structure

**Files:**
- Read: `毕设相关文件/毕设流程文件/毕业设计论文正文-完整Word版-含图片占位.txt`
- Create: `毕设相关文件/毕设流程文件/毕业设计论文正文-重构润色版.txt`

- [x] **Step 1: Extract headings**

Run:

```powershell
rg -n "^([0-9]+|[0-9]+\.[0-9]+|参考文献)" "毕设相关文件\毕设流程文件\毕业设计论文正文-完整Word版-含图片占位.txt"
```

Expected: chapter headings from `1 绪论` through `6 总结与展望` and `参考文献`.

- [x] **Step 2: Extract figure placeholders**

Run:

```powershell
rg -n "^【图片占位|^图 [0-9]" "毕设相关文件\毕设流程文件\毕业设计论文正文-完整Word版-含图片占位.txt"
```

Expected: all placeholders from 图 2-1 through 图 5-3 are visible and can be preserved.

### Task 2: Rewrite Strategy

**Files:**
- Create: `毕设相关文件/毕设流程文件/毕业设计论文正文-重构润色版.txt`

- [x] **Step 1: Keep stable thesis skeleton**

Use the following chapter structure:

```text
1 绪论
2 系统需求分析
3 系统总体设计
4 系统详细设计与实现
5 系统测试
6 总结与展望
参考文献
```

- [x] **Step 2: Define chapter-level rewrite goals**

Rewrite chapters with these goals:

```text
第 1 章：从毕业设计选题痛点引出智能双向选择系统的研究价值。
第 2 章：从角色、流程、功能与非功能需求说明系统为什么这样建。
第 3 章：从总体架构、分层、前端、数据库、接口和异步任务说明系统如何组织。
第 4 章：从核心模块实现说明业务闭环如何落地。
第 5 章：从后端、前端、联调和结果分析说明系统如何验证。
第 6 章：总结系统贡献、不足与后续优化方向。
```

### Task 3: Generate Reconstructed Thesis

**Files:**
- Create: `毕设相关文件/毕设流程文件/毕业设计论文正文-重构润色版.txt`

- [x] **Step 1: Write the reconstructed text**

Create a new text file rather than modifying the source file. Preserve the original image placeholder lines and reference list.

- [x] **Step 2: Keep Word-friendly formatting**

Use plain text only. Avoid Markdown list markers in thesis body. Keep Chinese full-width punctuation in Chinese prose, while retaining necessary English technical terms such as Flask, React, PostgreSQL, Redis, Docker Compose, REST, LLM, Worker, Adapter, Transformer, BERT and RAG.

### Task 4: Verify Output

**Files:**
- Verify: `毕设相关文件/毕设流程文件/毕业设计论文正文-重构润色版.txt`

- [x] **Step 1: Confirm file exists and line count**

Run:

```powershell
Get-Item -LiteralPath "毕设相关文件\毕设流程文件\毕业设计论文正文-重构润色版.txt" | Select-Object Name,Length,LastWriteTime
(Get-Content -LiteralPath "毕设相关文件\毕设流程文件\毕业设计论文正文-重构润色版.txt").Count
```

Expected: file exists and contains a complete thesis body.

- [x] **Step 2: Confirm required sections**

Run:

```powershell
rg -n "^([0-9]+|[0-9]+\.[0-9]+|参考文献)" "毕设相关文件\毕设流程文件\毕业设计论文正文-重构润色版.txt"
```

Expected: headings from `1 绪论` through `6 总结与展望` and `参考文献`.

- [x] **Step 3: Confirm placeholders are preserved**

Run:

```powershell
rg -n "^【图片占位|^图 [0-9]" "毕设相关文件\毕设流程文件\毕业设计论文正文-重构润色版.txt"
```

Expected: original figure placeholders and captions are present.
