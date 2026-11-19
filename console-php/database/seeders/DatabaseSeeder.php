<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Str;

class DatabaseSeeder extends Seeder
{
    /** Creates one admin and one read-only viewer. Never uses a hard-coded password. */
    public function run(): void
    {
        foreach ([['admin@example.com', 'admin', 'SEED_ADMIN_PASSWORD'], ['viewer@example.com', 'viewer', 'SEED_VIEWER_PASSWORD']] as [$email, $role, $envKey]) {
            $password = env($envKey) ?: Str::password(20);
            $user = User::firstOrNew(['email' => $email]);
            if (! $user->exists) {
                $user->forceFill(['name' => ucfirst($role), 'password' => $password, 'role' => $role])->save();
                if (! env($envKey)) {
                    $this->command?->warn("Created $email ($role) with generated password: $password");
                }
            }
        }
    }
}
