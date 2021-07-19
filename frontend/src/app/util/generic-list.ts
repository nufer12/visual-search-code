import { APIGenericDataItem, APIGenericDataFilter } from './data-types';
import { Subscriptable, ManagedSubs } from './managed-subs';
import { Input, Output, EventEmitter } from '@angular/core';

export abstract class GenericListItem<T> extends ManagedSubs {
    @Input() item : T// APIGenericDataItem;
}

export abstract class GenericList extends ManagedSubs {
    public bootstrapScale : number = -1;
    public paginationSettings : number[] = [0, 0];
}