<?php

use App\Http\Controllers\Web\DashboardController;
use App\Http\Controllers\Web\LoginController;
use Illuminate\Support\Facades\Route;

Route::redirect('/', '/leads');

Route::get('/login', [LoginController::class, 'show'])->name('login')->middleware('guest');
Route::post('/login', [LoginController::class, 'store'])->middleware(['guest', 'throttle:login']);
Route::post('/logout', [LoginController::class, 'destroy'])->name('logout')->middleware('auth');

// CSRF protection comes from the web middleware group (all POSTs below).
Route::middleware(['auth', 'role:admin,viewer'])->group(function () {
    Route::get('/leads', [DashboardController::class, 'leads'])->name('leads.index');
    Route::get('/conversations', [DashboardController::class, 'conversations'])->name('conversations.index');
    Route::get('/conversations/{conversation}', [DashboardController::class, 'conversation'])->name('conversations.show');
    Route::get('/evaluation-runs', [DashboardController::class, 'runs'])->name('runs.index');
    Route::get('/audit-events', [DashboardController::class, 'audit'])->name('audit.index');

    Route::post('/leads/{lead}/review', [DashboardController::class, 'reviewLead'])
        ->name('leads.review')->middleware('role:admin');
});
