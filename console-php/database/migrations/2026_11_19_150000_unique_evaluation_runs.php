<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    // The eval-reporter re-posts the same results; (run_key, model, defense) identifies a run so posts can upsert.
    public function up(): void
    {
        // Earlier versions allowed duplicate posts. Keep the newest row per run so the unique index can be created.
        $newest = DB::table('evaluation_runs')->selectRaw('max(id)')->groupBy('run_key', 'model', 'defense');
        DB::table('evaluation_runs')->whereNotIn('id', $newest)->delete();

        Schema::table('evaluation_runs', function (Blueprint $table) {
            $table->unique(['run_key', 'model', 'defense']);
        });
    }

    public function down(): void
    {
        Schema::table('evaluation_runs', function (Blueprint $table) {
            $table->dropUnique(['run_key', 'model', 'defense']);
        });
    }
};
