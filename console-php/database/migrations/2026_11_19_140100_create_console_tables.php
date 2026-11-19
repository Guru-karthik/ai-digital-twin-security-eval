<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('leads', function (Blueprint $table) {
            $table->id();
            $table->string('email', 254);
            $table->string('name', 200)->nullable();
            $table->text('notes')->nullable();
            $table->string('conversation_id')->nullable()->index();
            $table->string('status', 16)->default('pending')->index();
            $table->foreignId('reviewed_by')->nullable()->constrained('users')->nullOnDelete();
            $table->timestamps();
        });

        Schema::create('conversations', function (Blueprint $table) {
            $table->id();
            $table->string('external_id')->unique();
            $table->string('defense', 32)->nullable();
            $table->string('model', 100)->nullable();
            $table->json('messages');
            $table->unsignedInteger('message_count')->default(0);
            $table->timestamps();
        });

        Schema::create('evaluation_runs', function (Blueprint $table) {
            $table->id();
            $table->string('run_key')->index();
            $table->string('defense', 32)->index();
            $table->string('model', 100);
            $table->unsignedInteger('total_cases');
            $table->unsignedInteger('passed_cases');
            $table->double('attack_success_rate')->nullable();
            $table->double('mean_latency_s')->nullable();
            $table->double('cost_usd')->nullable();
            $table->json('failed_checks')->nullable();
            $table->timestamps();
        });

        Schema::create('audit_events', function (Blueprint $table) {
            $table->id();
            $table->string('type', 32)->index();
            $table->string('actor');
            $table->string('subject')->nullable();
            $table->json('detail')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('audit_events');
        Schema::dropIfExists('evaluation_runs');
        Schema::dropIfExists('conversations');
        Schema::dropIfExists('leads');
    }
};
