void func_us_801B001C(Entity* self) {
    s32 i;
    int new_var;
    s32 offset;
    Entity* newEntity;
    Entity* entityPool;
    s32 params;
    register s32 posX __asm__("$4");
    register s32 posY __asm__("$5");
    register s32 velocityY __asm__("$2");

    switch (self->step) {
    case 0:
        InitializeEntity(g_EInitInteractable);
        self->animSet = -0x7FFA;
        self->unk5A = 0x48;
        self->palette = 0x209;
        self->hitboxState = 2;
        if (self->params & 0x100) {
            self->facingLeft = 1;
        }
        self->zPriority -= 4;
        if (self->params == 1) {
            D_us_80180BA8 = 0;
        }
        params = (u8)self->params;
        self->animCurFrame = params;
        if (params < 5) {
            u8* hitbox;

            hitbox = D_us_80180D94;
            params--;
            hitbox += params * 12;
            self->hitboxWidth = *hitbox;
            hitbox += 2;
            self->hitboxHeight = *hitbox;
            hitbox += 2;
            self->hitboxOffX = *(u16*)hitbox;
            hitbox += 2;
            self->hitboxOffY = *(u16*)hitbox;
            hitbox += 2;
            self->hitPoints = *(u16*)hitbox;
            self->zPriority = *(u16*)(hitbox + 2);
            return;
        }
        self->step += params;
        return;

    case 1:
        if (self->flags & 0x100) {
            self->hitboxState = 0;
            self->step += (new_var = (u8)self->params);
        }
        return;

    case 2:
        self->animCurFrame = 0xA;
        if (GetSideToPlayer() & 1) {
            self->velocityX = 0x10000;
        } else {
            self->velocityX = -0x10000;
        }
        self->step = 0xB;
        return;

    case 3:
        i = 0;
        entityPool = g_Entities_224;
        offset = 0;
        for (; i < 4; i++, offset -= 0x1E) {
            newEntity = AllocEntity(entityPool, &entityPool[0x1780 / sizeof(Entity)]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(0x2A, self, newEntity);
                newEntity->params = i + 5;
                newEntity->posX.i.hi += 0x30 + offset;
            }
        }
        if (newEntity != NULL) {
            newEntity->params = 0x105;
        }
        for (i = 0, offset = 0; i < 4; i++, offset -= 0x1E) {
            newEntity = AllocEntity(entityPool, &entityPool[0x1780 / sizeof(Entity)]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(2, self, newEntity);
                {
                    register s32 spawnedParams __asm__("$2");
                    __asm__("li %0, 0x13"
                            : "=r"(spawnedParams)
                            : "r"(newEntity));
                    newEntity->params = spawnedParams;
                }
                newEntity->posX.i.hi += 0x30 + offset;
            }
        }
        {
            Entity* entity = &self[1];
            for (i = 0; i < 3; i++, entity++) {
                entity->flags |= FLAG_DEAD;
            }
        }
        self->animCurFrame = 0;
        self->step = 0x20;
        return;

    case 4:
        for (i = 0; i < 2; i++) {
            newEntity = AllocEntity(&g_Entities_224, &g_Entities_224[0x1780 / sizeof(Entity)]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(0x2A, self, newEntity);
                newEntity->params = i + 8;
                newEntity->posY.i.hi += i * 8;
                if (i != 0) {
                    if (GetSideToPlayer() & 1) {
                        newEntity->velocityX = 0x8000;
                    } else {
                        newEntity->velocityX = -0x8000;
                    }
                    newEntity->velocityY = -0x10000;
                }
            }
        }
        PlaySfxPositional(0x691);
        self->animCurFrame = 0;
        self->step = 0x20;
        return;

    case 5:
        i = 0;
        entityPool = g_Entities_224;
        offset = 0;
        for (; i < 3; i++, offset += 0x1C) {
            newEntity = AllocEntity(entityPool, &entityPool[0x1780 / sizeof(Entity)]);
            if (newEntity != NULL) {
                CreateEntityFromEntity(0x2A, self, newEntity);
                newEntity->params = i + 0xB;
                newEntity->posY.i.hi += -0x1C + offset;
            }
        }
        PlaySfxPositional(0x67F);
        self->animCurFrame = 0;
        self->step = 0x20;
        return;

    case 7:
    case 8:
        self->zPriority = 0x6A;
        MoveEntity();
        posX = self->posX.i.hi;
        posY = self->posY.i.hi + 8;
        self->velocityY = self->velocityY + 0x1000;
        if (func_us_801AD2F0(posX, posY) != 0) {
            self->step = 0x20;
        }
        return;

    case 9:
        self->zPriority = 0x6C;
        self->drawFlags |= 4;
        self->rotate -= 0x10;
        MoveEntity();
        posX = self->posX.i.hi;
        posY = self->posY.i.hi + 4;
        self->velocityY = self->velocityY + 0x1800;
        if (func_us_801AD2F0(posX, posY) != 0) {
            self->entityId = 2;
            self->pfnUpdate = EntityExplosion;
            self->params = 0;
            self->step = 0;
        }
        return;

    case 10:
        self->zPriority = 0x6C;
        self->drawFlags |= 4;
        self->rotate += 0x80;
        MoveEntity();
        posX = self->posX.i.hi;
        posY = self->posY.i.hi;
        velocityY = self->velocityY;
        self->velocityY = velocityY + 0x2000;
        if (func_us_801AD2F0(posX, posY) != 0) {
            self->entityId = 2;
            self->pfnUpdate = EntityExplosion;
            self->step = 0;
            self->params = 0;
        }
        return;

    case 11:
        self->zPriority = 0x6A;
        MoveEntity();
        posX = self->posX.i.hi;
        posY = self->posY.i.hi + 0xA;
        self->velocityY = self->velocityY + 0x1000;
        if (func_us_801AD2F0(posX, posY) != 0) {
            self->step = 0x20;
        }
        return;

    case 12:
        self->rotate -= 0x30;
        /* fall through */
    case 13:
        self->zPriority = 0x6B;
        self->drawFlags |= 4;
        self->rotate += 0x28;
        MoveEntity();
        posX = self->posX.i.hi;
        posY = self->posY.i.hi + 6;
        self->velocityY = self->velocityY + 0x1800;
        if (func_us_801AD2F0(posX, posY) != 0) {
            self->entityId = 2;
            self->pfnUpdate = EntityExplosion;
            self->params = 0;
            self->step = 0;
        }
        return;

    case 6:
    case 14:
        self->zPriority = 0x6A;
        return;
    }
}
