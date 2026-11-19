<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;

#[Fillable(['email', 'name', 'notes', 'conversation_id'])]
class Lead extends Model
{
    public const STATUSES = ['pending', 'approved', 'rejected'];

    /** status and reviewed_by are never mass-assigned; only the review action sets them. */
}
