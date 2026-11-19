<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;

#[Fillable(['email', 'name', 'notes', 'conversation_id'])]
class Lead extends Model
{
    public const STATUSES = ['pending', 'approved', 'rejected'];

    /** status and reviewed_by are never mass-assigned; only review() sets them. */

    /** Admin approve/reject and its audit event. A console feature, not agent-side human-in-the-loop. */
    public function review(string $status, User $admin): void
    {
        $this->forceFill(['status' => $status, 'reviewed_by' => $admin->id])->save();
        AuditEvent::create([
            'type' => 'admin_action',
            'actor' => $admin->email,
            'subject' => 'lead:'.$this->id,
            'detail' => ['status' => $status],
        ]);
    }
}
