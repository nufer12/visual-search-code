import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { GenericListItemComponent } from './generic-list-item.component';

describe('GenericListItemComponent', () => {
  let component: GenericListItemComponent;
  let fixture: ComponentFixture<GenericListItemComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ GenericListItemComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(GenericListItemComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
