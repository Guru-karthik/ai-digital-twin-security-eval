<?php

use App\Http\Controllers\Api\AuditEventController;
use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\ConversationController;
use App\Http\Controllers\Api\EvaluationRunController;
use App\Http\Controllers\Api\LeadController;
use Illuminate\Support\Facades\Route;

// Contract: docs/openapi.yaml. install:api mounts this file under /api.
Route::prefix('v1')->group(function () {
    Route::post('auth/login', [AuthController::class, 'login'])->middleware('throttle:login');

    // Machine callers (gateway, eval-reporter): service token, never a user token.
    Route::middleware(['service', 'throttle:service'])->group(function () {
        Route::post('leads', [LeadController::class, 'store']);
        Route::post('conversations', [ConversationController::class, 'store']);
        Route::post('evaluation-runs', [EvaluationRunController::class, 'store']);
        Route::post('audit-events', [AuditEventController::class, 'store']);
    });

    Route::middleware(['auth:sanctum', 'throttle:api'])->group(function () {
        Route::post('auth/logout', [AuthController::class, 'logout']);

        Route::middleware('role:admin,viewer')->group(function () {
            Route::get('leads', [LeadController::class, 'index']);
            Route::get('leads/{lead}', [LeadController::class, 'show']);
            Route::get('conversations', [ConversationController::class, 'index']);
            Route::get('conversations/{conversation}', [ConversationController::class, 'show']);
            Route::get('evaluation-runs', [EvaluationRunController::class, 'index']);
            Route::get('evaluation-runs/{evaluationRun}', [EvaluationRunController::class, 'show']);
            Route::get('audit-events', [AuditEventController::class, 'index']);
        });

        Route::patch('leads/{lead}', [LeadController::class, 'update'])->middleware('role:admin');
    });
});
