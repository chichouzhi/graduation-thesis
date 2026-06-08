<#
.SYNOPSIS
  Start the compose backend demo environment.

.DESCRIPTION
  Starts PostgreSQL, Redis, Flask web, and worker with a temporary compose
  override that publishes Flask to a configurable host port. It can also seed
  stable demo data and run backend API smoke checks.

.EXAMPLE
  .\scripts\start_backend_demo.ps1

.EXAMPLE
  .\scripts\start_backend_demo.ps1 -BackendPort 5051 -KeepData
#>
param(
    [Parameter(Mandatory = $false)]
    [int]$BackendPort = 5051,

    [Parameter(Mandatory = $false)]
    [switch]$SkipSeed,

    [Parameter(Mandatory = $false)]
    [switch]$SkipSmoke,

    [Parameter(Mandatory = $false)]
    [switch]$KeepData
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 240
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            return Invoke-RestMethod -Uri $Url -TimeoutSec 5
        } catch {
            Start-Sleep -Seconds 3
        }
    }

    throw "Timed out waiting for $Url"
}

function Invoke-JsonPost {
    param(
        [string]$Url,
        [hashtable]$Body,
        [hashtable]$Headers = @{}
    )

    $json = $Body | ConvertTo-Json -Depth 20 -Compress
    Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json" -Headers $Headers -Body $json
}

function Invoke-ApiGet {
    param(
        [string]$Url,
        [string]$Token
    )

    Invoke-RestMethod -Method Get -Uri $Url -Headers @{ Authorization = "Bearer $Token" }
}

function Write-ComposeOverride {
    param(
        [string]$Path,
        [int]$Port
    )

@"
services:
  web:
    ports:
      - "$Port`:5000"
"@ | Set-Content -Path $Path -Encoding utf8
}

function Invoke-DemoSeed {
    param(
        [string]$OverridePath,
        [bool]$KeepExistingData
    )

    $resetLine = if ($KeepExistingData) { "# keep existing data" } else { "db.drop_all()" }
    $seedScript = @"
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.identity.model import User, UserRole
from app.terms.model import Term
from app.topic.model import Topic, TopicStatus
from app.selection.model import Application, ApplicationFlowStatus, Assignment, AssignmentStatus
from app.taskboard.model import Milestone, MilestoneStatus

app = create_app()
with app.app_context():
    $resetLine
    db.create_all()

    now = datetime.utcnow()
    term = db.session.get(Term, "term-2026-spring")
    if term is None:
        term = Term(
            id="term-2026-spring",
            name="2026 Spring Graduation Project",
            selection_start_at=now - timedelta(days=30),
            selection_end_at=now + timedelta(days=30),
        )
        db.session.add(term)
    else:
        term.selection_start_at = now - timedelta(days=30)
        term.selection_end_at = now + timedelta(days=30)

    student = db.session.get(User, "user-student-demo")
    if student is None:
        student = User(id="user-student-demo", username="api-login-user", role=UserRole.student, display_name="Demo Student")
        db.session.add(student)
    student.username = "api-login-user"
    student.role = UserRole.student
    student.display_name = "Demo Student"
    student.email = "student@example.test"
    student.password_hash = generate_password_hash("correct-pass")
    student.student_profile = {
        "skills": ["React", "Flask", "async jobs", "academic writing"],
        "interests": ["AI academic assistant", "document analysis", "topic recommendation"],
        "research_direction": "AI academic productivity workspace",
    }

    teacher = db.session.get(User, "user-teacher-demo")
    if teacher is None:
        teacher = User(id="user-teacher-demo", username="teacher-demo", role=UserRole.teacher, display_name="Demo Teacher")
        db.session.add(teacher)
    teacher.username = "teacher-demo"
    teacher.role = UserRole.teacher
    teacher.display_name = "Demo Teacher"
    teacher.email = "teacher@example.test"
    teacher.password_hash = generate_password_hash("teacher-pass")
    teacher.teacher_profile = {"department": "Computer Science", "research_fields": ["software engineering", "LLM applications"]}

    admin = db.session.get(User, "user-admin-demo")
    if admin is None:
        admin = User(id="user-admin-demo", username="admin-demo", role=UserRole.admin, display_name="Demo Admin")
        db.session.add(admin)
    admin.username = "admin-demo"
    admin.role = UserRole.admin
    admin.display_name = "Demo Admin"
    admin.email = "admin@example.test"
    admin.password_hash = generate_password_hash("admin-pass")

    topic = db.session.get(Topic, "topic-1")
    if topic is None:
        topic = Topic(id="topic-1", teacher_id=teacher.id, term_id=term.id, capacity=2)
        db.session.add(topic)
    topic.title = "AI Academic Assistant Workspace"
    topic.summary = "A graduation-project workspace covering chat, document analysis, topic recommendation, and task tracking."
    topic.requirements = "Requires React, Flask, REST contracts, async task status flows, and thesis-oriented product explanation."
    topic.tech_keywords = ["React", "Flask", "LLM", "async queue", "PostgreSQL"]
    topic.capacity = 2
    topic.selected_count = 1
    topic.teacher_id = teacher.id
    topic.term_id = term.id
    topic.status = TopicStatus.published
    topic.portrait_json = {
        "keywords": ["AI academic assistant", "async task", "document analysis", "topic recommendation"],
        "difficulty_label": "medium-high",
        "difficulty_reason": "The project must connect LLM capability with graduation-project workflow and decouple execution through queues and workers.",
        "required_capabilities": ["frontend/backend integration", "contract reading", "task-state modeling"],
        "suitable_students": ["students with web full-stack basics", "students who can prepare an engineering demo"],
        "risks": ["async state synchronization", "thesis contribution must align with concrete requirements"],
        "summary": "Suitable for demonstrating engineering integration of LLMs in a graduation-project workflow.",
        "extracted_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    application = db.session.get(Application, "application-1")
    if application is None:
        application = Application(id="application-1", student_id=student.id, term_id=term.id, topic_id=topic.id, priority=1)
        db.session.add(application)
    application.student_id = student.id
    application.term_id = term.id
    application.topic_id = topic.id
    application.priority = 1
    application.status = ApplicationFlowStatus.accepted

    assignment = db.session.get(Assignment, "assignment-1")
    if assignment is None:
        assignment = Assignment(id="assignment-1", student_id=student.id, teacher_id=teacher.id, topic_id=topic.id, term_id=term.id)
        db.session.add(assignment)
    assignment.student_id = student.id
    assignment.teacher_id = teacher.id
    assignment.topic_id = topic.id
    assignment.term_id = term.id
    assignment.application_id = application.id
    assignment.status = AssignmentStatus.active
    assignment.confirmed_at = now

    milestone = db.session.get(Milestone, "milestone-1")
    if milestone is None:
        milestone = Milestone(id="milestone-1", student_id=student.id)
        db.session.add(milestone)
    milestone.student_id = student.id
    milestone.title = "Complete full-stack integration"
    milestone.description = "Verify frontend/backend integration with compose PostgreSQL, Redis, and worker."
    milestone.start_date = date(2026, 5, 1)
    milestone.end_date = date(2026, 5, 20)
    milestone.status = MilestoneStatus.doing
    milestone.sort_order = 1

    db.session.commit()
    print({
        "users": User.query.count(),
        "terms": Term.query.count(),
        "topics": Topic.query.count(),
        "applications": Application.query.count(),
        "assignments": Assignment.query.count(),
        "milestones": Milestone.query.count(),
    })
"@

    $seedScript | docker compose -f docker-compose.yml -f $OverridePath exec -T web python -
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Invoke-BackendSmoke {
    param([string]$BackendBaseUrl)

    $studentLogin = Invoke-JsonPost -Url "$BackendBaseUrl/api/v1/auth/login" -Body @{
        username = "api-login-user"
        password = "correct-pass"
    }
    $teacherLogin = Invoke-JsonPost -Url "$BackendBaseUrl/api/v1/auth/login" -Body @{
        username = "teacher-demo"
        password = "teacher-pass"
    }
    $studentToken = $studentLogin.access_token
    $teacherToken = $teacherLogin.access_token

    $me = Invoke-ApiGet -Url "$BackendBaseUrl/api/v1/users/me" -Token $studentToken
    $topics = Invoke-ApiGet -Url "$BackendBaseUrl/api/v1/topics?term_id=term-2026-spring&page=1&page_size=10" -Token $studentToken
    $recommendations = Invoke-ApiGet -Url "$BackendBaseUrl/api/v1/recommendations/topics?term_id=term-2026-spring&top_n=5&explain=true" -Token $studentToken
    $applications = Invoke-ApiGet -Url "$BackendBaseUrl/api/v1/applications?term_id=term-2026-spring&page=1&page_size=10" -Token $studentToken
    $teacherApplications = Invoke-ApiGet -Url "$BackendBaseUrl/api/v1/applications?term_id=term-2026-spring&topic_id=topic-1&page=1&page_size=10" -Token $teacherToken
    $assignments = Invoke-ApiGet -Url "$BackendBaseUrl/api/v1/assignments?page=1&page_size=10" -Token $studentToken
    $milestones = Invoke-ApiGet -Url "$BackendBaseUrl/api/v1/milestones?page=1&page_size=10" -Token $studentToken

    $conversation = Invoke-JsonPost -Url "$BackendBaseUrl/api/v1/conversations" -Headers @{ Authorization = "Bearer $studentToken" } -Body @{
        term_id = "term-2026-spring"
        title = "演示：毕业设计过程任务看板咨询"
        context_type = "topic"
        context_ref_id = "ee4c4719-26ea-4f38-a3e6-2e2d26482fff"
    }
    $accepted = Invoke-JsonPost -Url "$BackendBaseUrl/api/v1/conversations/$($conversation.id)/messages" -Headers @{ Authorization = "Bearer $studentToken" } -Body @{
        content = "我准备做“毕业设计过程任务看板与进度预警平台”，这个选题适合作为毕业设计吗？"
        client_request_id = "backend-smoke"
        seq = 1
    }

    $job = $null
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        $job = Invoke-ApiGet -Url "$BackendBaseUrl/api/v1/chat/jobs/$($accepted.job_id)" -Token $studentToken
        if ($job.status -in @("done", "failed")) {
            break
        }
    }

    [ordered]@{
        backend = $BackendBaseUrl
        user_id = $me.id
        username = $me.username
        topics_total = $topics.total
        recommendations_count = $recommendations.items.Count
        applications_total = $applications.total
        teacher_applications_total = $teacherApplications.total
        assignments_total = $assignments.total
        milestones_total = $milestones.total
        chat_initial_status = $accepted.assistant_message.status
        chat_job_status = $job.status
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$overridePath = Join-Path $env:TEMP "gd-compose-port-$BackendPort.yml"
$backendBaseUrl = "http://127.0.0.1:$BackendPort"

Set-Location -LiteralPath $repoRoot

Write-Step "Checking Docker Compose"
docker compose version | Out-Host

Write-Step "Writing temporary compose override: $overridePath"
Write-ComposeOverride -Path $overridePath -Port $BackendPort

Write-Step "Starting backend services on port $BackendPort"
docker compose -f docker-compose.yml -f $overridePath up -d postgres redis web worker
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Step "Waiting for backend health"
$health = Wait-HttpOk -Url "$backendBaseUrl/health" -TimeoutSeconds 240
if ($health.status -ne "healthy") {
    throw "Unexpected health response from $backendBaseUrl/health"
}

if (-not $SkipSeed) {
    Write-Step "Seeding backend demo data"
    Invoke-DemoSeed -OverridePath $overridePath -KeepExistingData ([bool]$KeepData)
}

if (-not $SkipSmoke) {
    Write-Step "Running backend smoke checks"
    $summary = Invoke-BackendSmoke -BackendBaseUrl $backendBaseUrl
    $summary | ConvertTo-Json -Depth 20
}

Write-Host ""
Write-Host "Backend demo is ready." -ForegroundColor Green
Write-Host "Backend: $backendBaseUrl"
Write-Host "Student: api-login-user / correct-pass"
Write-Host "Teacher: teacher-demo / teacher-pass"
Write-Host "Admin:   admin-demo / admin-pass"
Write-Host ""
Write-Host "Stop backend services:"
Write-Host "  docker compose -f docker-compose.yml -f `"$overridePath`" down"
