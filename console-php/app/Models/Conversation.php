<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;

#[Fillable(['external_id', 'defense', 'model', 'messages', 'message_count'])]
class Conversation extends Model
{
    protected function casts(): array
    {
        return ['messages' => 'array'];
    }
}
