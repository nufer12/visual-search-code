import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { ImageBoxesComponent } from './image-boxes.component';

describe('ImageBoxesComponent', () => {
  let component: ImageBoxesComponent;
  let fixture: ComponentFixture<ImageBoxesComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ ImageBoxesComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ImageBoxesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
